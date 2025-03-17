import hashlib
import json
import requests
from time import time
from flask import Flask, jsonify, request

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.nodes = set()

        # Create the Genesis block
        self.new_block(previous_hash="1", proof=100)

    def register_node(self, address):
        """Register a new node in the network."""
        self.nodes.add(address)

    def new_block(self, proof, previous_hash):
        """Create a new block and add it to the chain."""
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'votes': self.current_votes,
            'proof': proof,
            'previous_hash': previous_hash
        }
        self.current_votes = []  # Reset vote list
        self.chain.append(block)
        return block

    def new_vote(self, voter_id, candidate, signature):
        """Add a vote to the pending votes list."""
        self.current_votes.append({
            'voter_id': voter_id,
            'candidate': candidate,
            'signature': signature
        })
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """Generate a SHA-256 hash of a block."""
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """Simple Proof of Work Algorithm."""
        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """Validate the proof."""
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def valid_chain(self, chain):
        """Check if a blockchain is valid."""
        previous_block = chain[0]
        for index in range(1, len(chain)):
            block = chain[index]
            if block['previous_hash'] != self.hash(previous_block):
                return False
            if not self.valid_proof(previous_block['proof'], block['proof']):
                return False
            previous_block = block
        return True

    def resolve_conflicts(self):
        """Consensus Algorithm: Replaces chain with the longest valid chain in the network."""
        neighbors = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbors:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                data = response.json()
                length = data['length']
                chain = data['chain']
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True
        return False


# Flask Web API
app = Flask(__name__)
blockchain = Blockchain()


@app.route('/mine_block', methods=['GET'])
def mine_block():
    """Mine a new block containing pending votes."""
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block['proof'])
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': 'New block mined!',
        'index': block['index'],
        'timestamp': block['timestamp'],
        'votes': block['votes'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/get_chain', methods=['GET'])
def get_chain():
    """Retrieve the current blockchain."""
    response = {'chain': blockchain.chain, 'length': len(blockchain.chain)}
    return jsonify(response), 200


@app.route('/vote', methods=['POST'])
def vote():
    """Submit a new vote."""
    data = request.get_json()
    required_fields = ['voter_id', 'candidate', 'signature']
    if not all(field in data for field in required_fields):
        return 'Missing fields', 400

    index = blockchain.new_vote(data['voter_id'], data['candidate'], data['signature'])
    response = {'message': f'Vote will be added to Block {index}'}
    return jsonify(response), 201


@app.route('/register_node', methods=['POST'])
def register_node():
    """Register a new node in the blockchain network."""
    data = request.get_json()
    node = data.get('node')
    if node is None:
        return "Invalid node address", 400

    blockchain.register_node(node)
    response = {'message': 'New node registered!', 'nodes': list(blockchain.nodes)}
    return jsonify(response), 201


@app.route('/sync', methods=['GET'])
def sync():
    """Synchronize blockchain across the network."""
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {'message': 'Blockchain replaced with the longest chain!', 'chain': blockchain.chain}
    else:
        response = {'message': 'Blockchain already up-to-date.', 'chain': blockchain.chain}
    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

