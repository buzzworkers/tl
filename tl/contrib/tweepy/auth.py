# Tweepy
# Copyright 2009 Joshua Roesslein
# See LICENSE
from urllib.request import Request, urlopen
from urllib.parse import quote
import base64

from tweepy import oauth
from tweepy.error import TweepError
from tweepy.api import API


class AuthHandler(object):

    def apply_auth(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError


class BasicAuthHandler(AuthHandler):

    def __init__(self, username, password):
        self.username = username
        self._b64up = base64.b64encode(bytes('%s:%s' % (username, password), 'ascii'))

    def apply_auth(self, url, method, headers, parameters):
        headers['Authorization'] = 'Basic %s' % self._b64up.decode()

    def get_username(self):
        return self.username


class OAuthHandler(AuthHandler):

    REQUEST_TOKEN_URL = 'http://api.twitter.com/oauth/request_token'
    AUTHORIZATION_URL = 'http://api.twitter.com/oauth/authorize'
    AUTHENTICATE_URL = 'http://api.twitter.com/oauth/authenticate'
    ACCESS_TOKEN_URL = 'http://api.twitter.com/oauth/access_token'

    def __init__(self, consumer_key, consumer_secret, callback=None):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.username = None

    def apply_auth(self, url, method, headers, parameters):
        request = oauth.OAuthRequest.from_consumer_and_token(self._consumer,
            http_url=url, http_method=method, token=self.access_token, parameters=parameters)
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def _get_request_token(self):
        try:
            request = oauth.OAuthRequest.from_consumer_and_token(self._consumer,
                http_url = self.REQUEST_TOKEN_URL, callback=self.callback)
            request.sign_request(self._sigmethod, self._consumer, None)
            resp = urlopen(Request(self.REQUEST_TOKEN_URL,
                headers=request.to_header()), timeout=5.0)
            return oauth.OAuthToken.from_string(resp.read().decode())

        except Exception as e:
            raise TweepError(e)

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()

            # build auth request and return as url
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=self.AUTHORIZATION_URL)
            return request.to_url()

        except Exception as e:
            raise TweepError(e)

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=self.ACCESS_TOKEN_URL,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)

            # send request
            resp = urlopen(Request(self.ACCESS_TOKEN_URL, headers=request.to_header()))
            self.access_token = oauth.OAuthToken.from_string(resp.read().decode())
            return self.access_token
        except Exception as e:
            raise TweepError(e)

    def get_username(self):
        if self.username is None:
            api = API(self)
            user = api.verify_credentials()
            if user:
                self.username = user.screen_name
            else:
                raise TweepError("Unable to get username, invalid oauth token!")
        return self.username

