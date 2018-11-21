# ## Build configuration, tied to config.json in yocto-autobuilder-helpers
# Repositories used by each builder
buildertorepos = {
    "eclipse-plugin-neon": ["eclipse-poky-neon"],
    "eclipse-plugin-oxygen": ["eclipse-poky-oxygen"],
    "nightly": ["poky", "meta-intel", "oecore", "bitbake",
                "eclipse-poky-neon", "eclipse-poky-oxygen", "meta-qt4",
                "meta-qt3", "meta-mingw", "meta-gplv2"],
    "non-gpl3": ["poky", "meta-gplv2"],
    "qa-extras": ["poky", "meta-mingw"],
    "qemuarm-oecore": ["oecore", "bitbake"],
    "checkuri": ["poky", "meta-qt4", "meta-qt3"],
    "check-layer": ["poky", "meta-mingw", "meta-gplv2"],
    "default": ["poky"]
}

# Repositories used that the scripts need to know about and should be buildbot
# user customisable
repos = {
    "yocto-autobuilder-helper":
        ["git://git.yoctoproject.org/yocto-autobuilder-helper",
         "master"],
    "eclipse-poky-neon": ["git://git.yoctoproject.org/eclipse-yocto",
                          "neon-master"],
    "eclipse-poky-oxygen": ["git://git.yoctoproject.org/eclipse-yocto",
                            "oxygen-master"],
    "poky": ["git://git.yoctoproject.org/poky", "master"],
    "meta-intel": ["git://git.yoctoproject.org/meta-intel", "master"],
    "oecore": ["git://git.openembedded.org/openembedded-core",
                          "master"],
    "bitbake": ["git://git.openembedded.org/bitbake", "master"],
    "meta-qt4": ["git://git.yoctoproject.org/meta-qt4", "master"],
    "meta-qt3": ["git://git.yoctoproject.org/meta-qt3", "master"],
    "meta-mingw": ["git://git.yoctoproject.org/meta-mingw", "master"],
    "meta-gplv2": ["git://git.yoctoproject.org/meta-gplv2", "master"]
}

trigger_builders_wait = [
    "qemuarm", "qemuarm-lsb", "qemuarm64", "qemuarm-oecore",
    "qemumips", "qemumips-lsb", "qemumips64",
    "multilib",
    "qemuppc", "qemuppc-lsb",
    "qemux86", "qemux86-lsb",
    "qemux86-64", "qemux86-64-lsb",
    "qemux86-64-x32", "qemux86-world", "qemux86-world-lsb",
    "edgerouter", "edgerouter-lsb",
    "mpc8315e-rdb", "mpc8315e-rdb-lsb",
    "genericx86", "genericx86-lsb",
    "genericx86-64", "genericx86-64-lsb",
    "beaglebone", "beaglebone-lsb",
    "pkgman-non-rpm",
    "pkgman-rpm-non-rpm", "pkgman-deb-non-deb",
    "build-appliance", "buildtools", "eclipse-plugin-neon",
    "eclipse-plugin-oxygen", "non-gpl3", "wic",
    "poky-tiny", "musl-qemux86", "musl-qemux86-64", "no-x11",
    "qa-extras", "qa-extras2", "oe-selftest",
    "check-layer"
]

triggered_builders = trigger_builders_wait
builders = ["nightly"] + triggered_builders

# ## Cluster configuration
# Publishing settings
sharedrepodir = "/srv/www/vhosts/repos.yoctoproject.org"
publish_dest = "/srv/www/vhosts/autobuilder.yoctoproject.org/pub"

# Web UI settings
web_port = 8010

# List of workers in the cluster
workers = ["example-worker"]

# Worker configuration, all workers configured the same...
# TODO: support per-worker config
worker_password = "pass"
worker_max_builds = None
notify_on_missing = None

# Some builders should only run on specific workers (host OS dependent)
builder_to_workers = {
    "pkgman-rpm-non-rpm": [],
    "pkgman-deb-non-deb": [],
    "default": workers
}
