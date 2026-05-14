# keycloak_auth.py
"""OAuth2/OIDC клиент для Keycloak через Authlib."""

from authlib.integrations.flask_client import OAuth
from config.config_loader import get_config

oauth = OAuth()


def init_oauth(app) -> None:
    oauth.init_app(app)
    cfg = get_config().get('keycloak', {})
    server_url = cfg['server_url']
    realm = cfg['realm']
    oauth.register(
        name='keycloak',
        client_id=cfg['client_id'],
        client_secret=cfg['client_secret'],
        server_metadata_url=f'{server_url}/realms/{realm}/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
