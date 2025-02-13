import datetime
import hashlib
import json
from flask import Flask, request, jsonify
import requests
from uuid import uuid4

class Blockchain:
    def __init__(self):
        self.chain = []
        self.votes = []
        self.nodes = set()
        self.allowed_voters = {"voter1": "public_key1", "voter2": "public_key2"}
        self.create_block(proof=1, previous_hash='0')

    def create_block(self, proof, previous_hash):
        block={
                'index': len(self.chain)+1,
                'timestamp': str(datetime.datetime.now()),
                'proof': proof, 
                'previous_hash': previous_hash,
                'votes': self.votes
                }
        self.votes = []
        self.chain.append(block)
        return block

    def add_vote(self, voter_id, candidate, signature):
        if voter_id not in self.allowed_voters:
            return False
        vote = {'voter_id':voter_id, 'candidate': candidate, 'signature': signature}
        self.votes.append(vote)
        return True

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def get_previous_block(self):
        return self.chain[-1]

    def proof_of_authority(self):
        return hashlib.sha256(str(datetime.datetime.now()).encode()).hexdigest()[:5]

    def is_valid_chain(self, chain):
        for i in range(1, len(chain)):
            if chain[i]['previous_hash'] != self.hash(chain[i-1]):
                return False
            return True

    def register_node(self, address):
        self.nodes.add(address)

    def sync_chain(self):
        longest_chain = None
        max_length = len(self.chain)
        
        for node in self.nodes:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > max_length and self.is_valid_chain(chain):
                    max_length = length
                    longest_chain = chain

        if longest_chain: 
            self.chain = longest_chain
            return True
        return False

app = Flask(__name__)
node_identifier = str(uuid4()).replace('-','')
blockchain = Blockchain()

@app.route('/vote', methods=['POST'])
def vote():
    data = request.get_json()
    if not all(k in data for k in ['voter_id', 'candidate', 'signature']):
        return 'Missing parameters', 400

    if blockchain.add_vote(data['voter_id'], data['candidate'], data['signature']):
        return 'Vote added successfully', 201
    return 'Unauthorized voter', 403

@app.route('/mine_block', methods=['GET'])
def mine_block():
    previous_block = blockchain.get_previous_block()
    proof = blockchain.proof_of_authority()
    previous_hash = blockchain.hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)
    return jsonify(block), 200

@app.route('/get_chain', methods=['GET'])
def get_chain():
    return jsonify({'chain': blockchain.chain, 'length': len(blockchain.chain)}),200

@app.route('/register_node', methods=['POST'])
def register_node():
    data = request.get_json()
    blockchain.register_node(data['node'])
    return 'Node registered successfully', 201

@app.route('/sync', methods=['GET'])
def sync():
    replaced = blockchain.sync_chain()
    if replaced:
        return 'Chain updated', 200
    return 'Chain already up-to-date', 200

app.run(host='0.0.0.0', port=5000)

