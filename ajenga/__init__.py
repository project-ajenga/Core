import ajenga.default_config

config = ajenga.default_config


def init_config(config_):
    global config
    config = config_

    import ajenga.prelude
