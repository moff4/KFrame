#!/use/bin/env python3

import json

from ..basic_response import Response
from ...utils import CONTENT_JSON


class RestResponse(Response):
    def set_data(self, data):
        self._data = data

    def _extra_prepare_data(self) -> str:
        st = json.dumps(self._data)
        self.add_header(CONTENT_JSON)
        return st if isinstance(st, str) else st.decode()
