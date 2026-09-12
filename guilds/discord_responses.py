"""Bounded Discord responses that preserve full results and hide internal errors."""
import io
import json
import logging
import uuid
from contextlib import closing

import discord
import httpx
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from .modules.core import Invalid


def error_message(error):
    if isinstance(error, Invalid):return str(error)
    if isinstance(error, PermissionDenied):return 'Your guild role does not permit this action.'
    if isinstance(error, ObjectDoesNotExist):return 'That record no longer exists. Refresh your selection.'
    if isinstance(error, (KeyError, TypeError, ValueError)):return 'Invalid command input. Check the supplied fields.'
    if isinstance(error, (httpx.HTTPError, discord.HTTPException)):return 'Discord or an external service is unavailable or denied the request. Check permissions and retry.'
    reference=uuid.uuid4().hex[:12]
    logging.getLogger(__name__).error('Discord command failure reference=%s type=%s',reference,type(error).__name__)
    return f'An internal error prevented completion. Ask the operator to check reference {reference}.'


async def respond(interaction, result):
    """Follow a deferred interaction; long structured results become private files."""
    encoded=json.dumps(result,indent=2,ensure_ascii=False,default=str)
    if isinstance(result,str):content=result
    elif isinstance(result,dict):
        content='\n'.join(f'{key.replace("_"," ").title()}: '+(json.dumps(value,ensure_ascii=False) if isinstance(value,(dict,list)) else str(value)) for key,value in result.items()) or 'Done.'
    else:content=encoded
    content=discord.utils.escape_mentions(discord.utils.escape_markdown(content))
    if len(content.encode('utf-16-le'))//2<=1900:
        await interaction.followup.send(content,ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
    else:
        data=encoded.encode('utf-8')
        if len(data)>8*1024*1024:
            await interaction.followup.send('This result exceeds the attachment limit. Narrow the request or export it from the dashboard.',ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
            return
        with closing(discord.File(io.BytesIO(data),filename='openiq-result.json')) as attachment:
            await interaction.followup.send('Full result attached.',file=attachment,ephemeral=True,allowed_mentions=discord.AllowedMentions.none())
