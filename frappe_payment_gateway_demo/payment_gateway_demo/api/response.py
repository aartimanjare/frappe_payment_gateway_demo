"""One response shape for every endpoint, so frontends never guess."""


def ok(data=None, message: str = "") -> dict:
	"""
	Build a success response.

	Parameters:
		data (any, optional): The payload.
		message (str, optional): A short human-readable note.

	Returns:
		dict: {"status": True, "message": ..., "data": ...}
	"""
	return {"status": True, "message": message, "data": data}
