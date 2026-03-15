echo "Waiting for HAPI FHIR server to be ready..."
echo "This may take 60-90 seconds for Spring Boot initialization"
MAX_ATTEMPTS=60
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
  if curl -sf http://fhir:8080/fhir/metadata > /dev/null 2>&1; then
    echo "HAPI FHIR server is ready after $((ATTEMPT * 5)) seconds"
    sleep 10
    if [[ -d /ig-packages ]] ; then
      echo "Installing IG packages...";
      for package in /ig-packages/*.tgz; do
        if [ -f "$package" ]; then
            echo \"Installing $package\";
            BASE64_CONTENT=$(base64 -w 0 "$package")
            echo "$BASE64_CONTENT"

            curl -s \
                -X POST "http://fhir:8080/fhir/ImplementationGuide/\$install" \
                -H "Content-Type: application/json" \
                --data-binary @- <<EOF
            {
                "resourceType": "Parameters",
                "parameter": [
                    {
                    "name": "npmContent",
                    "valueBase64Binary": "$BASE64_CONTENT"
                    }
                ]
            }
EOF
        fi;
      done;
    fi;

    exit 0
  fi

  ATTEMPT=$((ATTEMPT + 1))
  echo "Attempt $ATTEMPT/$MAX_ATTEMPTS - waiting 5s..."
  sleep 5
done

echo "ERROR: HAPI FHIR server did not become ready in time"
