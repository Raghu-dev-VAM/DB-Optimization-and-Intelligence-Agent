"""
API Documentation and Testing Interface
Similar to Swagger for .NET - provides endpoint testing capabilities
"""

from http.server import BaseHTTPRequestHandler
import json

def generate_api_docs():
    """Generate API documentation HTML"""
    
    return """
<!DOCTYPE html>
<html>
<head>
    <title>SQL Agent API Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .endpoint { border: 1px solid #ddd; margin: 10px 0; padding: 15px; }
        .method { background: #007bff; color: white; padding: 5px 10px; border-radius: 3px; }
        .method.post { background: #28a745; }
        .method.get { background: #17a2b8; }
        button { background: #007bff; color: white; border: none; padding: 8px 15px; cursor: pointer; }
        textarea { width: 100%; height: 100px; }
        .response { background: #f8f9fa; padding: 10px; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>🤖 SQL Optimization Agent API</h1>
    <p><strong>Base URL:</strong> http://127.0.0.1:8020</p>
    
    <div class="endpoint">
        <h3><span class="method get">GET</span> /health</h3>
        <p>Check if the API is running</p>
        <button onclick="testEndpoint('/health', 'GET')">Test</button>
        <div id="health-response" class="response"></div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method get">GET</span> /api/multi-agent</h3>
        <p>Check multi-agent system status</p>
        <button onclick="testEndpoint('/api/multi-agent', 'GET')">Test</button>
        <div id="multi-agent-response" class="response"></div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method post">POST</span> /api/analyze</h3>
        <p>Regular SQL analysis (static + basic AI)</p>
        <textarea id="analyze-body" placeholder='{"sql": "SELECT * FROM Users", "db_type": "SQL Server"}'></textarea>
        <br><button onclick="testEndpoint('/api/analyze', 'POST', 'analyze-body')">Test</button>
        <div id="analyze-response" class="response"></div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method post">POST</span> /api/analyze-multi-agent</h3>
        <p>Full multi-agent analysis (Groq-powered)</p>
        <textarea id="multi-analyze-body" placeholder='{"sql": "SELECT * FROM Users WHERE UserId = 123", "analysis_type": "full_analysis", "db_type": "SQL Server"}'></textarea>
        <br><button onclick="testEndpoint('/api/analyze-multi-agent', 'POST', 'multi-analyze-body')">Test</button>
        <div id="multi-analyze-response" class="response"></div>
    </div>
    
    <div class="endpoint">
        <h3><span class="method get">GET</span> /api/history</h3>
        <p>Get analysis history</p>
        <button onclick="testEndpoint('/api/history', 'GET')">Test</button>
        <div id="history-response" class="response"></div>
    </div>
    
    <script>
        async function testEndpoint(url, method, bodyId = null) {
            const responseId = url.replace(/[^a-zA-Z]/g, '') + '-response';
            const responseDiv = document.getElementById(responseId);
            
            try {
                const options = {
                    method: method,
                    headers: {'Content-Type': 'application/json'}
                };
                
                if (bodyId) {
                    const body = document.getElementById(bodyId).value;
                    if (body.trim()) {
                        options.body = body;
                    }
                }
                
                responseDiv.innerHTML = '<em>Loading...</em>';
                
                const response = await fetch('http://127.0.0.1:8020' + url, options);
                const data = await response.json();
                
                responseDiv.innerHTML = `
                    <strong>Status:</strong> ${response.status}<br>
                    <strong>Response:</strong><br>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
            } catch (error) {
                responseDiv.innerHTML = `<strong>Error:</strong> ${error.message}`;
            }
        }
        
        // Pre-fill test data
        document.getElementById('analyze-body').value = JSON.stringify({
            "sql": "SELECT * FROM Users WHERE UserId = 123",
            "db_type": "SQL Server"
        }, null, 2);
        
        document.getElementById('multi-analyze-body').value = JSON.stringify({
            "sql": "CREATE PROCEDURE usp_GetUser @UserId INT AS BEGIN SELECT * FROM Users WHERE UserId = @UserId END",
            "analysis_type": "full_analysis",
            "db_type": "SQL Server"
        }, null, 2);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    with open("api_docs.html", "w") as f:
        f.write(generate_api_docs())
    print("✅ API documentation created: api_docs.html")
    print("📖 Open this file in your browser to test the API endpoints")