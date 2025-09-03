#!/bin/bash
# Privacy Guardian Demo Script

echo "🛡️ Privacy Guardian - End-to-End Demo"
echo "========================================="
echo ""

# Test Backend Health
echo "1. Testing Backend Health..."
curl -s http://localhost:8001/health | jq '.'
echo ""

# Upload the National Health Policy PDF
echo "2. Uploading National Health Policy PDF..."
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8001/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F 'file=@"1_National_Health_Policy .pdf"')

echo $UPLOAD_RESPONSE | jq '.'
POLICY_ID=$(echo $UPLOAD_RESPONSE | jq -r '.policy_id')
echo ""

# Test Translation Query
echo "3. Testing Plain English Translation..."
echo "Question: 'What are the main objectives of this health policy?'"
curl -s -X POST "http://localhost:8001/query" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What are the main objectives of this health policy?\",\"policy_id\":\"$POLICY_ID\"}" | jq '.'
echo ""

# Test Compliance Query
echo "4. Testing Compliance Analysis..."
echo "Question: 'Is this policy GDPR compliant for health data privacy?'"
curl -s -X POST "http://localhost:8001/query" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"Is this policy GDPR compliant for health data privacy?\",\"policy_id\":\"$POLICY_ID\"}" | jq '.'
echo ""

echo "✅ Demo Complete!"
echo "🌐 Frontend available at: http://localhost:3001"
echo "🔧 Backend API available at: http://localhost:8001"
echo "📚 API Docs available at: http://localhost:8001/docs"
