import os
import json

class RBACPolicyManager:
    def __init__(self, policy_path=None):
        if policy_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            policy_path = os.path.abspath(os.path.join(script_dir, "..", "config", "rbac_policy.json"))
            
        self.policy_path = policy_path
        self.policy_data = {}
        self.load_policy()
        
    def load_policy(self):
        try:
            if os.path.exists(self.policy_path):
                with open(self.policy_path, "r", encoding="utf-8") as f:
                    self.policy_data = json.load(f)
            else:
                print(f"[WARNING] RBAC Policy file not found at: {self.policy_path}")
        except Exception as e:
            print(f"[ERROR] Failed to load RBAC policy: {e}")
            
    def get_allowed_roles_for_resource(self, resource_id):
        # Default access rules
        rules = self.policy_data.get("resource_access_rules", {})
        
        # Check direct match (e.g. agr_hr08)
        if resource_id in rules:
            return rules[resource_id]
            
        # Check prefix match (e.g. if resource is agr_hr08_01, check prefix agr_hr08)
        for key, roles in rules.items():
            if str(resource_id).startswith(key):
                return roles
                
        # Default: if document starts with 'agr' (restricted internal policy)
        if str(resource_id).startswith("agr"):
            # Internal policies require at least Staff, Risk_Manager or Admin
            return ["Admin", "Risk_Manager", "Staff"]
            
        # Public external regulations are accessible by everyone
        return ["Admin", "HR", "Risk_Manager", "Staff", "Guest"]
        
    def is_access_granted(self, user_role, resource_id):
        allowed_roles = self.get_allowed_roles_for_resource(resource_id)
        return user_role in allowed_roles

if __name__ == "__main__":
    manager = RBACPolicyManager()
    print("Testing RBACPolicyManager:")
    print("  Access to 'agr_hr08' for HR:", manager.is_access_granted("HR", "agr_hr08"))
    print("  Access to 'agr_hr08' for Guest:", manager.is_access_granted("Guest", "agr_hr08"))
    print("  Access to 'external_regulations' for Guest:", manager.is_access_granted("Guest", "external_regulations"))
