#!/use/bin/env python3

import json

from ..basic_response import Response
from ...utils import CONTENT_JSON


class RestResponse(Response):
    name = 'rest_response'

    def set_data(self, data):
        self._data = data

    def _extra_prepare_data(self) -> str:
        st = json.dumps(self._data)
        self.add_headers(CONTENT_JSON)
        return st if isinstance(st, str) else st.decode()
