import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

class COREPEngine:
    def __init__(self):
        self.groq_key = os.getenv("GROQ_API_KEY")
        if not self.groq_key:
            raise ValueError("GROQ_API_KEY not found")
        
        self.client = Groq(api_key=self.groq_key)
        self.rules = self.load_file("rules.txt")
        self.schema = self.load_json_file("schema_c0100.json")
        self.validation_rules = self.load_json_file("validation_rules.json")
    
    def load_file(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"File not found: {filename}")
            return ""
    
    def load_json_file(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"JSON file not found: {filename}")
            return {}
    
    def process_query(self, user_input):
        """Main processing method - returns everything needed for GUI"""
        
        # Generate prompt
        prompt = self.generate_prompt(user_input)
        
        # Call LLM
        llm_response = self.call_llm(prompt)
        if not llm_response:
            return {"error": "LLM call failed"}
        
        # Parse response
        llm_data = self.parse_llm_response(llm_response)
        if not llm_data:
            return {"error": "Failed to parse response"}
        
        # Validate
        validation_results = self.validate_response(llm_data)
        
        # Prepare result
        result = {
            "success": True,
            "template_data": llm_data,
            "validation": validation_results,
            "timestamp": datetime.now().isoformat(),
            "user_query": user_input
        }
        
        return result
    
    def generate_prompt(self, user_scenario):
        """Generate prompt for LLM"""
        
        prompt = f"""You are a PRA COREP regulatory reporting assistant. Your task is to populate the COREP Own Funds template (C 01.00) based on the user's scenario.

REGULATORY RULES:
{self.rules}

COREP TEMPLATE SCHEMA (C 01.00 - CET1 Section):
{json.dumps(self.schema['sections']['CET1_Capital'], indent=2) if 'sections' in self.schema else '{}'}

USER SCENARIO:
{user_scenario}

INSTRUCTIONS:
1. Extract numerical values from the scenario
2. Apply COREP reporting rules exactly as specified
3. Calculate total CET1 capital (Row 100) = 010 + 020 + 030 + 040 - 070
4. Flag any missing or inconsistent data
5. Provide audit trail with specific rule references
6. Format all amounts as numbers without commas or currency symbols

REQUIRED OUTPUT FORMAT (JSON ONLY):
{{
  "template": "C 01.00",
  "reporting_date": "2024-12-31",
  "currency": "GBP",
  "data": {{
    "010": {{"value": "150000000", "description": "Ordinary share capital"}},
    "020": {{"value": "75000000", "description": "Share premium account"}},
    "030": {{"value": "300000000", "description": "Retained earnings"}},
    "040": {{"value": "25000000", "description": "Other comprehensive income"}},
    "070": {{"value": "45000000", "description": "Intangible assets (deduction)", "is_deduction": true}},
    "100": {{"value": "505000000", "description": "Total CET1 capital", "is_calculated": true}}
  }},
  "calculations": {{
    "CET1_formula": "010 + 020 + 030 + 040 - 070 = 150M + 75M + 300M + 25M - 45M = 505M"
  }},
  # In the generate_prompt method, make sure the example audit_trail is correct:
  "audit_trail": [
    {{"field": "010", "rule": "CRR Article 26(1)(a)", "justification": "Ordinary shares are CET1 eligible capital"}},
    {{"field": "020", "rule": "CRR Article 26(1)(b)", "justification": "Share premium account related to CET1 instruments"}},
    {{"field": "030", "rule": "CRR Article 26(1)(c)", "justification": "Retained earnings included in CET1"}},
    {{"field": "040", "rule": "CRR Article 26(1)(d)", "justification": "Other comprehensive income is CET1 component"}},
    {{"field": "070", "rule": "CRR Article 36(1)(b)", "justification": "Intangible assets must be deducted from CET1"}},
    {{"field": "100", "rule": "CRR Article 25", "justification": "Total CET1 = sum of components minus deductions"}}
  ],
  "validation_notes": [
    {{"type": "INFO", "message": "All required fields present", "fields": ["010", "020", "030", "100"]}}
  ]
}}

Return ONLY valid JSON. No explanations, no markdown, no additional text."""
        
        return prompt
    
    def call_llm(self, prompt):
        """Call Groq LLM API"""
        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[
                    {"role": "system", "content": "You are a regulatory reporting expert. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return None
    
    def parse_llm_response(self, response_text):
        """Parse and validate LLM response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            return None
    
    def validate_response(self, llm_data):
        """Validate the LLM response against schema and rules"""
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["010", "020", "030", "100"]
        for field_code in required_fields:
            if field_code not in llm_data.get("data", {}):
                errors.append(f"Missing required field: {field_code}")
            elif not llm_data["data"][field_code].get("value"):
                warnings.append(f"Empty value for field: {field_code}")
        
        # Check data types
        for field_code, field_data in llm_data.get("data", {}).items():
            value = field_data.get("value", "")
            if value and not re.match(r'^-?\d+$', str(value)):
                warnings.append(f"Non-numeric value in field {field_code}: {value}")
        
        # Validate CET1 calculation
        try:
            data = llm_data.get("data", {})
            components = 0
            deductions = 0
            
            # Sum components (positive values)
            for code in ["010", "020", "030", "040"]:
                if code in data:
                    val_str = data[code].get("value", "0")
                    if val_str:
                        components += int(val_str)
            
            # Sum deductions (negative values)
            for code in ["070"]:
                if code in data:
                    val_str = data[code].get("value", "0")
                    if val_str:
                        deductions += int(val_str)
            
            calculated_cet1 = components - deductions
            
            # Get reported CET1
            reported_cet1_str = data.get("100", {}).get("value", "0")
            reported_cet1 = int(reported_cet1_str) if reported_cet1_str else 0
            
            if calculated_cet1 != reported_cet1:
                errors.append(f"CET1 calculation mismatch: Calculated {calculated_cet1:,} vs Reported {reported_cet1:,}")
            
            # Check CET1 positivity
            if reported_cet1 < 0:
                errors.append(f"CET1 is negative: {reported_cet1:,}")
                
        except ValueError as e:
            warnings.append(f"Calculation error: {e}")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0
        }