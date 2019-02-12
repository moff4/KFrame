#!/use/bin/env python3

import json

from ..basic_response import Response
from ...utils import CONTENT_JSON


class RestResponse(Response):
    def set_data(self, data):
        self.data = data

    def _extra_prepare_data(self):
        st = json.dumps(self.data)
        self.add_header(CONTENT_JSON)
        return st if isinstance(st, bytes) else st.encode()
