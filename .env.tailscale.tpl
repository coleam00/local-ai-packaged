# Tailnet ingress (DockTail) secrets — resolved from 1Password at run time via `op run`.
# One FRESH OAuth client (tag:server; scopes Auth-Keys + Devices-Core + Services = Write).
# 1Password item: "Tailscale-localai-docktail"  (username = client-id, credential = secret).
# The sidecar mints its tag:server auth key from the OAuth secret; DockTail uses the client
# id+secret to manage Services. Never inline these; never commit a resolved .env.
TS_AUTHKEY=op://Private/Tailscale-localai-docktail/credential
TAILSCALE_OAUTH_CLIENT_ID=op://Private/Tailscale-localai-docktail/username
TAILSCALE_OAUTH_CLIENT_SECRET=op://Private/Tailscale-localai-docktail/credential
