class InvalidActionType(Exception):
    """Some action in the spec file is not valid"""
    def __init__(self, action_str):
        msg = f'Invalid action {action_str}'
        super().__init__(self, msg)
        self.action = action_str


class InvalidActionDescription(Exception):
    """The action could not be parsed properly"""
    pass


class InvalidPackageException(Exception):
    """Something happened when trying to parse the package"""
    pass
