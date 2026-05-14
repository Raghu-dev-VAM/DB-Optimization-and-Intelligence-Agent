"""
Groq Client for SQL Agent System
Provides fast, powerful AI responses using Groq's llama-3.3-70b-versatile model
"""

import json
import os
import re
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None

from agent_config import sql_agent_system

class GroqClient:
    """Groq AI client - tries primary key first, fallback key second"""
    
    def __init__(self):
        self.config = sql_agent_system
        self.groq_client = None
        self.fallback_client = None
        
        if not GROQ_AVAILABLE:
            print("[GROQ] ERROR: Groq SDK not installed")
            return

        primary_key = self.config.groq_config["api_key"]
        fallback_key = os.getenv("GROQ_API_KEY_FALLBACK")

        if primary_key:
            try:
                self.groq_client = Groq(api_key=primary_key)
                print("[GROQ] PRIMARY key loaded")
            except Exception as e:
                print(f"[GROQ] PRIMARY key init failed: {e}")

        if fallback_key:
            try:
                self.fallback_client = Groq(api_key=fallback_key)
                print("[GROQ] FALLBACK key loaded")
            except Exception as e:
                print(f"[GROQ] FALLBACK key init failed: {e}")

        if not self.groq_client and not self.fallback_client:
            print("[GROQ] ERROR: No valid Groq API key found")
    
    def call_ai(self, system_message: str, user_prompt: str, timeout: int = 30) -> Dict[str, Any]:
        """Call Groq AI - tries primary key first, fallback second"""

        if not self.groq_client and not self.fallback_client:
            raise Exception("No Groq client available. Check API keys and internet connection.")

        clients = []
        if self.groq_client:
            clients.append(("PRIMARY", self.groq_client))
        if self.fallback_client:
            clients.append(("FALLBACK", self.fallback_client))

        last_error = None
        for label, client in clients:
            try:
                start_time = datetime.now()
                response = client.chat.completions.create(
                    model=self.config.groq_config["model"],
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.config.groq_config["temperature"],
                    max_tokens=self.config.groq_config["max_tokens"],
                    timeout=timeout
                )
                content = response.choices[0].message.content
                processing_time = (datetime.now() - start_time).total_seconds()
                print(f"[GROQ] {label} key succeeded in {processing_time:.2f}s")

                try:
                    json_content = self._extract_json(content)
                    json_content["processing_time"] = processing_time
                    json_content["ai_provider"] = "groq"
                    return json_content
                except:
                    return {
                        "reasoning": content,
                        "confidence": 0.8,
                        "processing_time": processing_time,
                        "ai_provider": "groq"
                    }
            except Exception as e:
                print(f"[GROQ] {label} key failed: {e}")
                last_error = e
                continue

        raise Exception(f"Both Groq keys failed. Last error: {str(last_error)}")
    
    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from AI response"""
        
        # Look for JSON block
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Look for plain JSON
        json_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        raise ValueError("No valid JSON found in response")

# Global instance
groq_client = GroqClient()

def test_groq_client():
    """Test Groq client functionality"""
    
    print("Testing Groq Client...")
    
    system_message = "You are a helpful SQL analysis assistant."
    user_prompt = """Analyze this SQL and respond in JSON format:
    
    SELECT * FROM Users WHERE UserId = 123
    
    Respond with:
    {
        "analysis": "brief analysis",
        "issues": ["list of issues"],
        "confidence": 0.0-1.0
    }"""
    
    try:
        result = groq_client.call_ai(system_message, user_prompt)
        
        print("SUCCESS: Groq Client Test Results:")
        print(f"   Provider: {result.get('ai_provider', 'unknown')}")
        print(f"   Processing Time: {result.get('processing_time', 0):.2f}s")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"   Response Keys: {list(result.keys())}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Test failed: {e}")
        return False

if __name__ == "__main__":
    test_groq_client()