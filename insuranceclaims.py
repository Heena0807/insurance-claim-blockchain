import hashlib
import json
import time
import os

class Block:
    # Changed the constructor to properly handle the block_hash argument
    def __init__(self, index, timestamp, data, prev_hash, block_hash=None):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.prev_hash = prev_hash
        
        if block_hash:
            self.hash = block_hash
        else:
            self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.timestamp}{json.dumps(self.data)}{self.prev_hash}"
        return hashlib.sha256(block_string.encode()).hexdigest()

class Blockchain:
    def __init__(self):
        self.chain = []
        self.claim_states = {}
        self.claims_registry = {}
        self.file_path = 'blockchain.json'
        self.load_chain()

    def create_genesis_block(self):
        return Block(0, time.time(), {"type": "GENESIS"}, "0")

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data):
        latest_block = self.get_latest_block()
        new_block = Block(len(self.chain), time.time(), data, latest_block.hash)
        self.chain.append(new_block)
        
        if 'claim_id' in data:
            claim_id = data['claim_id']
            current_state = self.claim_states.get(claim_id, {})
            updated_state = {**current_state, **data}
            self.claim_states[claim_id] = updated_state
        
        if data.get("type") == "CLAIM_CREATE":
            claim_key = self.generate_claim_key(data['policy_id'], data['hospital'], data['treatment'])
            self.claims_registry[claim_key] = True
        
        self.save_chain()

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]
            
            # This check is what validates the entire chain.
            # It checks if the hash of the previous block, which is stored in the current block, is correct.
            if current.prev_hash != prev.hash:
                print(f"Block {current.index} prev_hash is invalid! It does not match the hash of the previous block.")
                return False

            # This check is crucial for detecting external changes.
            # It ensures the data within the current block hasn't been tampered with.
            if current.hash != current.calculate_hash():
                print(f"Block {current.index} hash is invalid! The data in the block has been altered.")
                return False
            
        return True

    def get_claim_data(self, claim_id):
        return self.claim_states.get(claim_id)

    def generate_claim_key(self, policy_id, hospital, treatment):
        key = f"{policy_id}-{hospital}-{treatment}"
        return key.lower().replace(" ", "")

    def is_duplicate_claim(self, policy_id, hospital, treatment):
        claim_key = self.generate_claim_key(policy_id, hospital, treatment)
        return self.claims_registry.get(claim_key, False)
    
    def get_patient_history(self, patient_name):
        history = []
        for claim_id, state in self.claim_states.items():
            if state.get("patient_name", "").lower() == patient_name.lower():
                history.append(state)
        return history

    def print_chain(self):
        for block in self.chain:
            print(f"Index: {block.index}")
            print(f"Timestamp: {block.timestamp}")
            print(f"PrevHash: {block.prev_hash[:16]}...")
            print(f"Hash:      {block.hash[:16]}...")
            print(f"Data: {json.dumps(block.data, indent=2)}\n")

    def save_chain(self):
        data_to_save = {
            'chain': [vars(block) for block in self.chain],
            'claim_states': self.claim_states,
            'claims_registry': self.claims_registry
        }
        with open(self.file_path, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print("Blockchain saved successfully.")

    def load_chain(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                self.chain = []
                for b in data['chain']:
                    block = Block(b['index'], b['timestamp'], b['data'], b['prev_hash'], b['hash'])
                    self.chain.append(block)
                
                self.claim_states = data.get('claim_states', {})
                self.claims_registry = data.get('claims_registry', {})
            print("Blockchain loaded from file.")
        else:
            self.chain = [self.create_genesis_block()]
            print("No existing blockchain found. Creating a new one.")


def main():
    bc = Blockchain()

    while True:
        print("\n==== Insurance Claim (v11) ====")
        print("1) Add new claim")
        print("2) Approve claim")
        print("3) Reject claim")
        print("4) Settle a claim")
        print("5) View patient history")
        print("6) Print full chain")
        print("7) Validate blockchain")
        print("8) Exit")
        choice = input("Choice: ")

        if choice == "1":
            policy_id = input("Policy ID: ")
            patient_name = input("Patient Name: ")
            hospital = input("Hospital: ")
            treatment = input("Treatment: ")
            claim_amount = float(input("Claim Amount: "))

            if bc.is_duplicate_claim(policy_id, hospital, treatment):
                print("❌ Duplicate claim detected. A claim for this policy, hospital, and treatment already exists.")
            else:
                claim_id = "C" + str(int(time.time()))[-6:]
                claim_data = {
                    "type": "CLAIM_CREATE",
                    "claim_id": claim_id,
                    "policy_id": policy_id,
                    "patient_name": patient_name,
                    "hospital": hospital,
                    "treatment": treatment,
                    "claim_amount": claim_amount,
                    "status": "Pending",
                    "approvals_needed": 2,
                    "approvals_from": []
                }
                bc.add_block(claim_data)
                print(f"\n✅ Claim created with ClaimID: {claim_id}")

        elif choice == "2":
            claim_id = input("Enter ClaimID to approve: ")
            officer = input("Officer Name: ")
            claim_data = bc.get_claim_data(claim_id)

            if not claim_data:
                print("❌ Claim not found.")
            elif officer in claim_data.get("approvals_from", []):
                print(f"❌ Officer {officer} has already approved this claim.")
            elif claim_data.get("status") in ["Approved", "Rejected", "Settled"]:
                print(f"❌ Claim is already {claim_data['status']}.")
            else:
                updated_data = claim_data.copy()
                updated_approvals = updated_data.get("approvals_from", [])
                
                updated_approvals.append(officer)
                approvals_needed = updated_data.get("approvals_needed", 2)

                new_status = "Pending"
                if len(updated_approvals) >= approvals_needed:
                    new_status = "Approved"

                update_data_block = {
                    "type": "CLAIM_UPDATE",
                    "claim_id": claim_id,
                    "status": new_status,
                    "approvals_from": updated_approvals,
                    "approved_by": officer
                }
                bc.add_block(update_data_block)
                
                if new_status == "Approved":
                    print(f"\n✅ Claim {claim_id} approved by {officer}. It has now reached the required number of approvals.")
                else:
                    print(f"\n✅ Claim {claim_id} approved by {officer}. {approvals_needed - len(updated_approvals)} more approval(s) needed.")

        elif choice == "3":
            claim_id = input("Enter ClaimID to reject: ")
            officer = input("Officer Name: ")
            reason = input("Reason for rejection: ")
            claim_data = bc.get_claim_data(claim_id)

            if not claim_data:
                print("❌ Claim not found.")
            elif claim_data.get("status") in ["Approved", "Rejected", "Settled"]:
                print(f"❌ Claim is already {claim_data['status']}.")
            else:
                update_data = {
                    "type": "CLAIM_UPDATE",
                    "claim_id": claim_id,
                    "status": "Rejected",
                    "rejected_by": officer,
                    "reason": reason
                }
                bc.add_block(update_data)
                print(f"\n❌ Claim {claim_id} rejected by {officer} (Reason: {reason})")

        elif choice == "4":
            claim_id = input("Enter ClaimID to settle: ")
            claim_data = bc.get_claim_data(claim_id)

            if not claim_data:
                print("❌ Claim not found.")
            elif claim_data.get("status") != "Approved":
                print(f"❌ Claim must be 'Approved' before it can be settled. Current status: {claim_data.get('status')}")
            else:
                settlement_data = {
                    "type": "CLAIM_SETTLEMENT",
                    "claim_id": claim_id,
                    "status": "Settled",
                    "settlement_date": time.time(),
                    "paid_amount": claim_data.get("claim_amount"),
                    "settled_by": "System"
                }
                bc.add_block(settlement_data)
                print(f"\n✅ Claim {claim_id} settled. Payment of {claim_data.get('claim_amount')} recorded.")
        
        elif choice == "5":
            patient_name = input("Enter patient name: ")
            history = bc.get_patient_history(patient_name)
            if history:
                print(f"\n--- History for {patient_name} ---")
                for record in history:
                    display_record = record.copy() 
                    
                    if display_record.get("settlement_date"):
                        timestamp = display_record["settlement_date"]
                        display_record["settlement_date"] = time.ctime(timestamp)

                    print(json.dumps(display_record, indent=2))
                    print("-" * 20)
            else:
                print("❌ No claims found for this patient.")

        elif choice == "6":
            bc.print_chain()

        elif choice == "7":
            print("Blockchain valid:", bc.is_chain_valid())

        elif choice == "8":
            print("Exiting...")
            break
        
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()
