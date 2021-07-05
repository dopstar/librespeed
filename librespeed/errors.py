class LibreSpeedBaseError(Exception):
    pass


class ParameterConflictError(LibreSpeedBaseError):
    pass


class HttpError(LibreSpeedBaseError):
    pass
