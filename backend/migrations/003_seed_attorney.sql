-- Default credentials for local development:
--   email:    attorney@alma.com
--   password: alma2024
--
-- To regenerate the hash:
--   python3 -c "import bcrypt; print(bcrypt.hashpw(b'<password>', bcrypt.gensalt(12)).decode())"
INSERT INTO attorneys (email, password_hash) VALUES (
  'attorney@alma.com',
  '$2b$12$CUBi1SUuxaQldjqyHhtJfOy0ZM/UXDsZJ6/RlCG6O9muc.WwVqbbW'
);
