from authlib.integrations.flask_oauth2.requests import FlaskJsonRequest
from authlib.integrations.flask_oauth2.signals import token_authenticated
from authlib.oauth2 import OAuth2Error
from authlib.oauth2 import ResourceProtector as BaseResourceProtector
from authlib.oauth2.rfc6749 import MissingAuthorizationError
from flask import g
from flask import request as flask_request

from src.constants import ANONYMOUS_USER_ID_HEADER


class AllowAnonymousResourceProtector(BaseResourceProtector):
    def acquire_token(self, scopes=None, **kwargs):
        """A method to acquire current valid token with the given scope.

        :param scopes: a list of scope values
        :return: token object
        """
        request = FlaskJsonRequest(flask_request)
        # backward compatibility
        kwargs["scopes"] = scopes
        for claim in kwargs:
            if isinstance(kwargs[claim], str):
                kwargs[claim] = [kwargs[claim]]
        token = self.validate_request(request=request, **kwargs)
        token_authenticated.send(self, token=token)
        g.authlib_server_oauth2_token = token
        return token

    # this is partially adapted from authlib's ResourceProtector.__call__ wrapper
    # https://github.com/lepture/authlib/blob/1cba9804e8684f92b34b0f2b80dbb5c93795ce9c/authlib/integrations/flask_oauth2/resource_protector.py#L97
    def get_token(self, **kwargs):
        claims = kwargs

        try:
            return self.acquire_token(**claims)

        # this DOES NOT handle missing scopes properly
        # if we add an admin page we'll need to make sure we use the provider that requires a login
        except MissingAuthorizationError:
            return flask_request.headers.get(ANONYMOUS_USER_ID_HEADER)

        except OAuth2Error:
            return None
