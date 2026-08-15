"""Placeholder channels for real messaging providers. Not implemented in the MVP —
wire these up only after a client signs a pilot and official API access is available."""
from __future__ import annotations

from channels.base import MessageChannel


class MetaWhatsAppChannel(MessageChannel):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "MetaWhatsAppChannel requires Meta WhatsApp Cloud API credentials — "
            "configure this only after a client pilot is approved."
        )


class TwilioChannel(MessageChannel):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "TwilioChannel requires a Twilio account and WhatsApp-enabled number — "
            "not needed for the demo/MVP stage."
        )


class GupshupChannel(MessageChannel):
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "GupshupChannel requires Gupshup API credentials — "
            "not needed for the demo/MVP stage."
        )
