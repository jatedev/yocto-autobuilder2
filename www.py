from buildbot.plugins import util
from yoctoab import config


# allow = []
#
# for builder in config.builders:
#     allow.append(util.ForceBuildEndpointMatcher(builder=builder, role='*'))
#     allow.append(util.StopBuildEndpointMatcher(builder=builder, role='*'))
#
# authz = util.Authz(
#     stringsMatcher=util.fnmatchStrMatcher,
#     allowRules=allow,
#     roleMatchers=[])
# auth = util.HTPasswdAuth('/home/pokybuild/.htpasswd')
#
# www = dict(port=config.web_port,
#            auth=auth,
#            authz=authz,
#            plugins=dict(waterfall_view={}, console_view={}, grid_view={}))

www = dict(port=config.web_port,
           plugins=dict(waterfall_view={}, console_view={}, grid_view={}))
