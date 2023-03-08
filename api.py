import requests
import json
import random
import re

class ApiError(Exception):
    pass

class RegistrationError(ApiError):
    pass

class LoginError(ApiError):
    pass

class PasswordError(ApiError):
    pass


class KennisHubAPI:
    def __init__(self, base_url="https://admin.kennishub.nl/api/v1/", response_format="json"):
        self.base_url = base_url
        self.format = response_format
    
    def validate_title_and_description(self, title, description):
        if not title:
            raise ValueError('Titel is verplicht')
        if not description:
            raise ValueError('Een korte beschrijving is verplicht')
        if len(description) > 280:
            raise ValueError('Er zijn maximaal 280 karakters toegestaan')

    def validate_link_and_title(self, url, title):
        if not title:
            raise ValueError('Een titel is verplicht.')
        if not url:
            raise ValueError('Een bron is verplicht')
        pattern = re.compile(r'^((https?):\/\/)?(www.)?[a-z0-9-]+(\.[a-z]{2,}){1,3}(#?\/?[a-zA-Z0-9#-]+)*\/?(\?[a-zA-Z0-9-_]+=[a-zA-Z0-9-%]+&?)?$')
        if not pattern.match(url):
            raise ValueError('Vul een valide url in')
        if len(description) > 180:
            raise ValueError('Informatie over deze bron mag maar 180 karakters zijn.')
    
    def validate_message(self, message):
        if not message:
            raise ValueError('Een bericht is verplicht')
        if len(message) > 144:
            raise ValueError('Een bericht mag maximaal 144 karakters zijn')
    
    def input2slug(self, input):
        slug = input.lower().replace(' ', '-')
        return slug

    def login_user(self, email, password):
        endpoint = f"{self.base_url}user/login"
        data = {
            "email": email,
            "password": password
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = requests.post(endpoint, data=json.dumps(data), headers=headers)

        if response.status_code == 200:
            data = response.json()
            if not data.get("status"):
                raise LoginError("Onjuiste gebruikersnaam of wachtwoord")
        else:
            response.raise_for_status()
        
    def register_user(self, name, email, function, password, url=""):
        endpoint = f"{self.base_url}user/register"
        data = {
            "name": name,
            "email": email,
            "function": function,
            "url": url,
            "password": password
        }
        if len(password) < 8:
            raise RegistrationError("Je wachtwoord moet minimaal 8 karakters bevatten.")
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = requests.post(endpoint, data=json.dumps(data), headers=headers)

        if response.status_code == 200:
            data = response.json()
            if not data.get("status"):
                raise RegistrationError("Er is iets mis gegaan met registreren, probeer het later nog eens. Of probeer je wachtwoord te resetten.")
        elif response.status_code == 401:
            raise RegistrationError("Wachtwoord is verplicht.")
        else:
            response.raise_for_status()

    def reset_password(self, email):
        endpoint = f"{self.base_url}user/reset_password"
        data = {
            "email": email
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = requests.post(endpoint, data=json.dumps(data), headers=headers)

        if response.status_code == 200:
            data = response.json()
            if not data.get("status"):
                error_message = data.get("message")
                if error_message and "The selected E-mailadres is invalid." in error_message:
                    raise PasswordError("Invalid email address")
                else:
                    raise PasswordError("Unknown error")
        else:
            response.raise_for_status()


    def verify_email(self, id, hash_value, expires, signature):
        endpoint = f"{self.base_url}email/verify/{id}/{hash_value}"
        params = {
            "expires": expires,
            "signature": signature
        }
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = requests.get(endpoint, params=params, headers=headers)

        if response.status_code != 200:
            raise InvalidVerificationLink("Invalid verification link")

        data = response.json()
        return data
    '''
    Verify email will look something like this
    https://admin.kennishub.nl/api/v1/email/verify/92/b0392efa4c2c2e3e0dd017df3254d9ffaf438af3?expires=1677581044&signature=72451f4e4e23c2337086c812ecd41927da5a5b4d743ca2b5b25013e04244ec17
    '''
    
    def get_user_info(self, token: str) -> dict:
        endpoint = f"{self.base_url}user/details"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        response = requests.get(endpoint, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == True:
                return data["data"]
            else:
                raise ValueError(data["message"])
        else:
            response.raise_for_status()

    def create_topic(self, token, title, description):
        self.validate_title_and_description(title, description)
        endpoint = f"{self.base_url}topics/create"
        params = {
            "title": title,
            "description": description
            }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(endpoint,headers=headers,params=params)
        if response.status_code == 200:
            data = response.json()
            if data['status']:
                return data['data']
            else:
                raise ValueError(data['message'])
        else:
            response.raise_for_status()

    def follow_topic(self, token, topic_id):
        endpoint = f"{self.base_url}topics/{topic_id}/follow-topic"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(endpoint,headers=headers)
        if self.format == "json":
            return response.json()
        else:
            return response.text

    def get_topics_list(self, token, sort_order='desc'):
        endpoint = f"{self.base_url}topics/list"
        params = {"sortOrder": sort_order}
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(endpoint,headers=headers,params=params)
        response.raise_for_status()
        data = response.json().get('data', [])

        selected_info = []
        for topic in data:
            topics_info = {
                'topic_id': topic.get('id'),
                'user_id': topic.get('user_id'),
                'title': topic.get('title'),
                'topic_slug': topic.get('slug'),
                'description': topic.get('description'),
                'topic_created_at': topic.get('created_at'),
                'topic_updated_at': topic.get('updated_at'),
                'topic_human_readable_created_at': topic.get('human_readable_created_at'),
                'user_name': topic.get('user', {}).get('name'),
                'user_slug': topic.get('user', {}).get('slug'),
            }
            selected_info.append(topics_info)
        
        return selected_info

    def get_profile(self, token, input_name):
        slug = self.input2slug(input_name)
        endpoint = f"{self.base_url}user/profile/{slug}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(endpoint, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data['status']:
                return data['data']
            else:
                raise ValueError(data['message'])
        else:
            response.raise_for_status()
    

    def forgot_password(self, email):
        endpoint = f"{self.base_url}user/forgot-password"
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        data = {
            "email": email
        }
        response = requests.post(endpoint, data=json.dumps(data), headers=headers)

        if self.format == "json":
            return response.json()
        else:
            return response.text

    def send_posts_replies(self, token, title, description, topic_id, url=""):
        self.validate_link_and_title(url, title)
        endpoint = f"{self.base_url}posts/create"
        params = {
            "title": title,
            "description": description,
            "topic_id": topic_id,
            "url": url
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(endpoint, params=params, headers=headers)
        if self.format == "json":
            return response.json()
        else:
            return response.text

    def send_reply_comment(self, token, message, post_id):
        endpoint = f"{self.base_url}comments/{post_id}/create"
        params = {
            "message": message
        }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(endpoint, params=params, headers=headers)
        if self.format == "json":
            return response.json()
        else:
            return response.text

    def get_topics_replies(self, token, input_topic, sort_by='created_at', sort_order='desc'):
        topic_slug = self.input2slug(input_topic)
        url = f"{self.base_url}posts/list"
        params = {
            "topic_slug": topic_slug,
            "sortBy": sort_by,
            "sortOrder": sort_order
            }
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, params=params)
        data = response.json().get('data', [])

        selected_info = []
        for post in data:
            post_info = {
                'title': post.get('title'),
                'description': post.get('description'),
                'url': post.get('url'),
                'post_id': post.get('id'),
                'post_date': post.get('human_readable_created_at'),
                'user_name': post.get('user', {}).get('name'),
                'user_slug': post.get('user', {}).get('slug'),
                'upvotes_count': post.get('upvotes_count'),
                'comments_count': post.get('comments_count'),
                'post_created_at': post.get('user', {}).get('created_at'),
                'post_updated_at': post.get('user', {}).get('updated_at')
            }
            selected_info.append(post_info)
        
        return selected_info

