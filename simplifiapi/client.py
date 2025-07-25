import logging
import requests
import uuid
from urllib.parse import urljoin

logger = logging.getLogger("simplifiapi")

SIMPLIFI_ENDPOINT = "https://services.quicken.com"


class Client():

    def __init__(self):
        self.session = requests.Session()

    def start_login(self, email, password):
        # Step 1: Oauth authorize
        body = {
            "clientId": "acme_web",
            "mfaChannel": None,
            "mfaCode": None,
            "password": password,
            "redirectUri": "https://app.simplifimoney.com/login",
            "responseType": "code",
            "threatMetrixRequestId": None,
            "threatMetrixSessionId": str(uuid.uuid4()),
            "username": email,
        }
        r = self.session.post(
            url="https://services.quicken.com/oauth/authorize", json=body)
        data = r.json()
        status = data.get("status")

        if (status == "MFA code sent"):
            return {
              "body": body,
              "mfa_channel": data.get("mfaChannel"),
              "status": status
            }

        if "accessToken" in data:
            self.access_token = data["accessToken"]
            return {"status": "success"}

        errors = data.get("errors")
        raise RuntimeError("Unexpected login status: " + errors[0]["detail"])

    def finish_login(self, mfa_code: str, body: dict, mfa_channel: str):
        if mfa_code:
              mfaCode = mfa_code
              logger.info("Using provided MFA code")
        else:
              mfaCode = input("MFA Code: ")
        body["mfaChannel"] = mfa_channel
        body["mfaCode"] = mfaCode
        r = requests.post(
           url="https://services.quicken.com/oauth/authorize", json=body)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if (status != "User passed MFA"):
            logger.error("Login failed.")
            logger.error(r.json())
            return False
        else:
            return r.json().get("code")
    
    def get_token(self, code):
        # Step 2: Get token
        r = self.session.post(url="https://services.quicken.com/oauth/token",
                              json={
                                  "clientId": "acme_web",
                                  "clientSecret": "BCDCxXwdWYcj@bK6",
                                  "grantType": "authorization_code",
                                  "code": code,
                                  "redirectUri": "https://app.simplifimoney.com/login"
                              })
        r.raise_for_status()
        token = r.json().get("accessToken")

        logger.warn("Retrieved token {}".format(token))

        return token

    def verify_token(self, token) -> bool:
        headers = {"Authorization": "Bearer {}".format(token)}

        r = self.session.get(url="https://services.quicken.com/userprofiles/me",
                             headers=headers)
        if (r.status_code != 200):
            logger.error("Error code: {}".format(r.status_code))
            logger.error(r.json())
            return False
        data = r.json()
        userId = data.get("id")
        logger.warn("User {} logged in.".format(userId))

        # Update session
        self.session.headers.update(headers)

        return True

    def _unpaginate(self, path: str, **kargs):
        nextLink = path
        data = []
        while nextLink:
            logger.warn("Fetching {}".format(nextLink))
            r = self.session.get(url=urljoin(
                SIMPLIFI_ENDPOINT, nextLink), **kargs)
            r.raise_for_status()
            data.extend(r.json()["resources"])
            nextLink = r.json().get("metaData").get("nextLink")
        return data

    def get_datasets(self, limit: int = 1000):
        return self._unpaginate(path="/datasets",
                                params={
                                    limit: limit,
                                })

    def get_accounts(self, datasetId: str):
        return self._unpaginate(path="/accounts",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_transactions(self, datasetId: str):
        return self._unpaginate(path="/transactions",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_tags(self, datasetId: str):
        return self._unpaginate(path="/tags",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })

    def get_categories(self, datasetId: str):
        return self._unpaginate(path="/categories",
                                headers={
                                     "Qcs-Dataset-Id": datasetId,
                                },
                                params={
                                    "limit": 1000,
                                })
