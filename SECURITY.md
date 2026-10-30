# Security policy

The latest successful BIRD 3 build on Alpine 3.24 is the actively maintained image. Older revision tags are retained for traceability and are not patched in place. Upgrade to a current digest to receive fixes.

For BIRD vulnerabilities, follow https://bird.nic.cz/contact/ and contact upstream privately. For container packaging vulnerabilities, use this repository's GitHub private vulnerability reporting feature if available. Otherwise contact a maintainer through their public GitHub profile to arrange a private channel before sharing exploit details. Do not post credentials or private routing configurations in public issues. No response-time guarantee is provided.

The release gate blocks HIGH/CRITICAL CVEs with fixes known to Trivy and fails closed on scanner errors. It does not establish that an image has no vulnerabilities. Runtime permissions, host kernel security, routing policy, and protecting the control socket are the operator's responsibility.
