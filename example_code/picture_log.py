import dataclasses


@dataclasses.dataclass
class SimplePictureLog:
    content: dict

    def render(self, request):
        request.event['picture'] = self.content

    @classmethod
    def own(cls):
        return cls(
            {
                'action': 'access_own_pictures'
            }
        )

    @classmethod
    def raw(cls, public_id: int):
        return cls(
            {
                'requested_picture_id': public_id,
                'action': 'access_raw'
            }
        )

    @classmethod
    def upload(cls):
        return cls(
            {
                'action': 'upload'
            }
        )

    @classmethod
    def download(cls, public_id: int):
        return cls(
            {
                'requested_picture_id': public_id,
                'action': 'download'
            }
        )

    def form_valid(self, is_valid: bool, error: str = ''):
        self.content['form_valid'] = is_valid
        if error:
            self.content['form_error'] = error
        return self

    def is_public(self, public: bool):
        self.content['is_public'] = public
        return self

    def is_owner(self, owner: bool):
        self.content['is_owner'] = owner
        return self

    def set_id(self, public_id):
        self.content['requested_picture_id'] = public_id
        return self

    def thumbnail(self, is_thumbnail:bool):
        self.content['is_thumbnail'] = is_thumbnail
        return self


