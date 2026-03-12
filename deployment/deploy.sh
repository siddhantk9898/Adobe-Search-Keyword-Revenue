#!/bin/bash
# ============================================================
# Deployment script for Search Keyword Performance Processor
# Uses AWS SAM CLI to build and deploy the Lambda function.
# ============================================================

set -e

STACK_NAME="adobe-search-keyword-processor"
REGION="us-east-1"
TEMPLATE_FILE="deployment/template.yaml"

echo "========================================="
echo "  Building SAM application..."
echo "========================================="
sam build --template-file "$TEMPLATE_FILE"

echo ""
echo "========================================="
echo "  Deploying to AWS ($REGION)..."
echo "========================================="
sam deploy \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --capabilities CAPABILITY_IAM \
    --resolve-s3 \
    --no-confirm-changeset

echo ""
echo "========================================="
echo "  Deployment complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Upload data.sql to the S3 bucket under the 'input/' prefix:"
echo "     aws s3 cp data.sql s3://<bucket-name>/input/data.sql"
echo ""
echo "  2. Or invoke the Lambda manually:"
echo "     aws lambda invoke --function-name SearchKeywordPerformanceProcessor \\"
echo "       --payload '{\"bucket\": \"<bucket-name>\", \"key\": \"input/data.sql\"}' \\"
echo "       response.json"
echo ""
echo "  3. Check the output in S3:"
echo "     aws s3 ls s3://<bucket-name>/output/"
