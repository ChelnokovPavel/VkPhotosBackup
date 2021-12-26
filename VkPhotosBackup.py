import logging
from time import sleep
import requests
from tqdm import tqdm
import yaml


class VkPhotosBackup:

    def __init__(self, user_id, vk_token, yadisk_token,
                 yadisk_dir_name, file_format):
        self.user_id = user_id
        self.vk_token = vk_token
        self.vk_api_version = '5.131'
        self.vk_url = 'https://api.vk.com/method'
        self.yadisk_url = 'https://cloud-api.yandex.net'
        self.yadisk_headers = {'Authorization': yadisk_token}
        self.yadisk_dir_name = yadisk_dir_name
        self.file_format = file_format

    def _create_dir(self):
        res = requests.get(url=f'{self.yadisk_url}/v1/disk/resources',
                           headers=self.yadisk_headers,
                           params={'path': f'/{self.yadisk_dir_name}'})
        if res.status_code != 200:
            requests.put(url=f'{self.yadisk_url}/v1/disk/resources',
                         headers=self.yadisk_headers,
                         params={'path': f'/{self.yadisk_dir_name}'})
            logging.info('Directory VkBackup is created')
        else:
            logging.info('Directory VkBackup is exists. Nothing to do')

    def _check_file_exists(self, file_name):
        res = requests.get(url=f'{self.yadisk_url}/v1/disk/resources',
                           headers=self.yadisk_headers,
                           params={'path': f'/{self.yadisk_dir_name}/{file_name}.{self.file_format}'})
        if not res.json().get('error'):
            return True

    def _get_upload_link(self, file_name):
        i = 1
        while self._check_file_exists(file_name, file_format):
            file_name = f'{file_name}_{i}'
            i += 1
        params = {'path': f'/{self.yadisk_dir_name}/{file_name}.{self.file_format}', 'overwrite': 'true'}
        res = requests.get(url=f'{self.yadisk_url}/v1/disk/resources/upload',
                           headers=self.yadisk_headers,
                           params=params)
        if res.json().get('href'):
            return res.json()['href']
        raise KeyError(f'Key href is empty')

    def yadisk_upload(self, binary, file_name):
        href = self._get_upload_link(file_name)
        res = requests.put(url=href, data=binary)
        res.raise_for_status()
        if res.status_code != 201:
            return True

    def execute(self):
        self._create_dir()
        vk_params = {
            'access_token': self.vk_token,
            'v': self.vk_api_version,
            'owner_id': self.user_id,
            'album_id': 'profile',
            'extended': 1,
            'photo_sizes': 1,
            'count': 1000
        }
        offset = 0
        photos_list = []
        while True:
            vk_params['offset'] = offset
            photos = requests.get(f'{self.vk_url}/photos.get', params=vk_params)
            if not photos.json()['response']['items']:
                break
            photos_list += photos.json()['response']['items']
            offset += 1000
            sleep(0.5)
        logging.info(f'Upload {len(photos_list)} photo(s)')
        for i, photo in enumerate(tqdm(photos_list)):
            likes = photo['likes']['count']
            max_size_url = photo['sizes'][-1]['url']
            res = requests.get(max_size_url)
            if self.yadisk_upload(res.content, likes):
                logging.error(f'\n{offset + i} photo,\n'
                              f'Upload unsuccessful. Status_code: {res.status_code}')


if __name__ == '__main__':

    logging.getLogger().setLevel(logging.INFO)

    with open('options.yaml') as file:
        options = yaml.safe_load(file)

    user_id = input('Please enter vkontakte user id')
    if not options['vk_token']:
        vk_token = input('Please enter vkontakte token')
    if not options['yadisk_token']:
        yadisk_token = input('Please enter yandex disk token')

    new_obj = VkPhotosBackup(user_id=user_id,
                             vk_token=vk_token,
                             yadisk_token=yadisk_token,
                             yadisk_dir_name=options['yadisk_dir_name'],
                             file_format=options['file_format'])

    new_obj.execute()

    logging.info('Done')
