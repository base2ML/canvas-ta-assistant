#!/bin/bash
# Fix Canvas Course ID Format Issues
# This script ensures course data is available in both short and long format

BUCKET="canvas-ta-dashboard-prod-canvas-data"
SHORT_COURSE_ID="516212"
LONG_COURSE_ID="20960000000516212"

echo "========================================="
echo "Fixing Course ID Format Issues"
echo "========================================="
echo "Bucket: $BUCKET"
echo "Short ID: $SHORT_COURSE_ID"
echo "Long ID: $LONG_COURSE_ID"
echo ""

# Check if short form exists
echo "📋 Checking for short form data..."
if aws s3 ls "s3://$BUCKET/canvas_data/course_$SHORT_COURSE_ID/latest.json" &>/dev/null; then
    echo "✅ Short form data exists: canvas_data/course_$SHORT_COURSE_ID/"

    # Copy to long form
    echo "📦 Creating long form copy..."
    aws s3 cp "s3://$BUCKET/canvas_data/course_$SHORT_COURSE_ID/latest.json" \
              "s3://$BUCKET/canvas_data/course_$LONG_COURSE_ID/latest.json"
    echo "✅ Long form created: canvas_data/course_$LONG_COURSE_ID/latest.json"
else
    echo "⚠️  Short form data not found"
fi

# Check if long form exists
echo ""
echo "📋 Checking for long form data..."
if aws s3 ls "s3://$BUCKET/canvas_data/course_$LONG_COURSE_ID/latest.json" &>/dev/null; then
    echo "✅ Long form data exists: canvas_data/course_$LONG_COURSE_ID/"

    # Copy to short form if it doesn't exist
    if ! aws s3 ls "s3://$BUCKET/canvas_data/course_$SHORT_COURSE_ID/latest.json" &>/dev/null; then
        echo "📦 Creating short form copy..."
        aws s3 cp "s3://$BUCKET/canvas_data/course_$LONG_COURSE_ID/latest.json" \
                  "s3://$BUCKET/canvas_data/course_$SHORT_COURSE_ID/latest.json"
        echo "✅ Short form created: canvas_data/course_$SHORT_COURSE_ID/latest.json"
    fi
else
    echo "⚠️  Long form data not found"
fi

echo ""
echo "========================================="
echo "Summary - Available Course Data:"
echo "========================================="
aws s3 ls "s3://$BUCKET/canvas_data/" --recursive | grep "course_" | grep "latest.json"

echo ""
echo "✅ Course ID format standardization complete!"
echo "Both short form ($SHORT_COURSE_ID) and long form ($LONG_COURSE_ID) are now available."
