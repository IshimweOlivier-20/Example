# Reflection - Formative 2

## What I Learned

This formative assignment helped me understand how to implement real security features in a Django REST API. The most challenging part was getting the encryption to work properly with the database fields and making sure the audit logging captured every sensitive data access.

## Challenges Faced

Setting up field-level encryption was difficult at first because I had to understand how Fernet encryption works and how to integrate it with Django's ORM. The rate limiting also required careful configuration to ensure it blocked brute-force attempts without blocking legitimate users.

The audit logging middleware took several attempts to get right. I learned that tracking read access is just as important as tracking writes for compliance purposes.

## Skills Gained

- Implementing JWT and session-based authentication
- Using Django middleware for security headers and audit logging
- Field-level encryption with cryptography library
- Rate limiting and throttling in DRF
- Role-based access control (RBAC)

## What I Would Do Differently

If I started over, I would plan the security architecture before writing any code. I also spent too much time debugging the encryption key configuration, which taught me to read the documentation more carefully first.

Overall, this project showed me why security cannot be an afterthought—it needs to be built into the system from the beginning.
