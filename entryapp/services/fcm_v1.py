from __future__ import annotations

import json
import os
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings

from google.auth.transport.requests import Request
from google.oauth2 import service_account


FCM_SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'


def _load_service_account_info() -> dict[str, Any] | None:
    raw_json = getattr(settings, 'FCM_SERVICE_ACCOUNT_JSON', '').strip() or os.environ.get('FCM_SERVICE_ACCOUNT_JSON', '').strip()
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            return None

    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '').strip()
    if credentials_path and os.path.exists(credentials_path):
        try:
            with open(credentials_path, 'r', encoding='utf-8') as fp:
                return json.load(fp)
        except OSError:
            return None

    return None


def _get_project_id(service_account_info: dict[str, Any]) -> str | None:
    from_settings = getattr(settings, 'FCM_PROJECT_ID', '').strip() or os.environ.get('FCM_PROJECT_ID', '').strip()
    if from_settings:
        return from_settings

    project_id = service_account_info.get('project_id')
    if isinstance(project_id, str) and project_id.strip():
        return project_id.strip()
    return None


def _get_access_token(service_account_info: dict[str, Any]) -> str:
    credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=[FCM_SCOPE])
    credentials.refresh(Request())
    token = credentials.token
    if not token:
        raise RuntimeError('Unable to obtain Google OAuth access token for FCM.')
    return token


def send_fcm_push(target: str, title: str, body: str, payload: dict[str, Any] | None = None):
    info = _load_service_account_info()
    if not info:
        return False, 'FCM service account JSON is not configured (FCM_SERVICE_ACCOUNT_JSON).'

    project_id = _get_project_id(info)
    if not project_id:
        return False, 'FCM project id is not configured (FCM_PROJECT_ID) and not found in service account JSON.'

    try:
        access_token = _get_access_token(info)
    except Exception as exc:
        return False, f'FCM auth failed: {exc}'

    message: dict[str, Any] = {
        'notification': {
            'title': title,
            'body': body,
        },
    }

    if target.startswith('/topics/'):
        message['topic'] = target.replace('/topics/', '', 1)
    else:
        message['token'] = target

    if payload:
        # FCM data fields must be string values.
        message['data'] = {str(k): str(v) for k, v in payload.items()}

    request_body = {'message': message}
    endpoint = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'
    request = urllib_request.Request(
        endpoint,
        data=json.dumps(request_body).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json; charset=UTF-8',
        },
        method='POST',
    )

    try:
        with urllib_request.urlopen(request, timeout=10) as response:
            response_body = response.read().decode('utf-8')
        return True, response_body
    except urllib_error.HTTPError as exc:
        body_text = exc.read().decode('utf-8', errors='replace') if hasattr(exc, 'read') else str(exc)
        return False, f'HTTP {exc.code}: {body_text}'
    except urllib_error.URLError as exc:
        return False, str(exc)
