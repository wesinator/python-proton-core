from ..exceptions import *
from .base import Transport

import json, base64, asyncio, aiohttp, hashlib
from OpenSSL import crypto
from typing import Iterable, Union, Optional

# It's stupid, but we have to inherit from aiohttp.Fingerprint to trigger the correct logic in aiohttp
class AiohttpCertkeyFingerprint(aiohttp.Fingerprint):
    def __init__(self, fingerprints: Optional[Iterable[Union[bytes, str]]]) -> None:
        if fingerprints is not None:
            self._fingerprints = []
            for fp in fingerprints:
                if type(fp) == str:
                    self._fingerprints.append(base64.b64decode(fp))
                else:
                    self._fingerprints.append(fp)
        else:
            self._fingerprints = None


    def check(self, transport: asyncio.Transport) -> None:
        if not transport.get_extra_info("sslcontext"):
            return
        sslobj = transport.get_extra_info("ssl_object")
        cert = sslobj.getpeercert(binary_form=True)

        cert_obj = crypto.load_certificate(crypto.FILETYPE_ASN1, cert)
        pubkey_obj = cert_obj.get_pubkey()
        pubkey = crypto.dump_publickey(crypto.FILETYPE_ASN1, pubkey_obj)

        pubkey_hash = hashlib.sha256(pubkey).digest()

        if pubkey_hash not in self._fingerprints:
            # Dump certificate, so we can diagnose if needed with:
            # base64 -d|openssl x509 -text -inform DER 
            raise ProtonAPINotReachable(f"TLS pinning verification failed: {base64.b64encode(cert)}")


class AiohttpTransport(Transport):
    def __init__(self, session):
        super().__init__(session)

    @classmethod
    def _get_priority(cls):
        return 10

    @property
    def tls_pinning_hashes(self):
        return self._environment.tls_pinning_hashes

    @property
    def http_base_url(self):
        return self._environment.http_base_url

    async def async_api_request(
        self, endpoint,
        jsondata=None, additional_headers=None,
        method=None, params=None
    ):
        if self.tls_pinning_hashes is not None:
            ssl_specs = AiohttpCertkeyFingerprint(self.tls_pinning_hashes)
        else:
            # Validate SSL normally if we didn't have fingerprints
            import ssl
            ssl_specs = ssl.create_default_context()
            ssl_specs.verify_mode = ssl.CERT_REQUIRED

        async with aiohttp.ClientSession() as s:
            s.headers['x-pm-appversion'] = self._session.appversion
            s.headers['User-Agent'] = self._session.user_agent
            if self._session.authenticated:
                s.headers['x-pm-uid'] = self._session.UID
                s.headers['Authorization'] = 'Bearer ' + self._session.AccessToken
            s.headers.update(self._environment.http_extra_headers)

            # If we don't have an explicit method, default to get if there's no data, post otherwise
            if method is None:
                if jsondata is None:
                    fct = s.get
                else:
                    fct = s.post
            else:
                fct = {
                    'get': s.get,
                    'post': s.post,
                    'put': s.put,
                    'delete': s.delete,
                    'patch': s.patch
                }.get(method.lower())

                if fct is None:
                    raise ValueError("Unknown method: {}".format(method))

            try:
                async with fct(self.http_base_url + endpoint, headers=additional_headers, json=jsondata, params=params, ssl = ssl_specs) as ret:
                    if ret.headers['content-type'] != 'application/json':
                        raise ProtonAPINotReachable("API returned non-json results")
                    try:
                        ret_json = await ret.json()
                    except json.decoder.JSONDecodeError:
                        raise ProtonAPIError(ret.status, dict(ret.headers), {})

                if ret_json['Code'] not in [1000, 1001]:
                    raise ProtonAPIError(ret.status, dict(ret.headers), ret_json)

                return ret_json
            except aiohttp.ClientConnectorCertificateError as e:
                raise ProtonAPINotReachable(f"SSL validation failed: {e}")
            except ProtonAPINotReachable:
                raise
            except ProtonAPIError:
                raise
            except (Exception) as e:
                raise ProtonAPIUnexpectedError(e)

