# ## Build configuration, tied to config.json in yocto-autobuilder-helpers
# Repositories used by each builder
buildertorepos = {
    "eclipse-plugin-neon": ["eclipse-poky-neon"],
    "eclipse-plugin-oxygen": ["eclipse-poky-oxygen"],
    "nightly": ["poky", "meta-intel", "oecore", "bitbake",
                "eclipse-poky-neon", "eclipse-poky-oxygen", "meta-qt4",
                "meta-qt3", "meta-mingw", "meta-gplv2"],
    "nightly-non-gpl3": ["poky", "meta-gplv2"],
    "nightly-qa-extras": ["poky", "meta-mingw"],
    "nightly-oecore": ["oecore", "bitbake"],
    "nightly-checkuri": ["poky", "meta-qt4", "meta-qt3"],
    "nightly-check-layer": ["poky", "meta-mingw", "meta-gplv2"],
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
    "nightly-arm", "nightly-arm-lsb", "nightly-arm64",
    "nightly-mips", "nightly-mips-lsb", "nightly-mips64",
    "nightly-multilib", "nightly-x32",
    "nightly-ppc", "nightly-ppc-lsb",
    "nightly-x86-64", "nightly-x86-64-lsb",
    "nightly-x86", "nightly-x86-lsb",
    "nightly-packagemanagers",
    "nightly-rpm-non-rpm", "nightly-deb-non-deb",
    "build-appliance", "buildtools", "eclipse-plugin-neon",
    "eclipse-plugin-oxygen", "nightly-non-gpl3", "nightly-oecore",
    "nightly-world", "nightly-wic", "nightly-world-lsb",
    "poky-tiny", "nightly-musl", "nightly-musl-x86-64", "nightly-no-x11",
    "nightly-qa-extras", "nightly-oe-selftest", "nightly-check-layer"
]

triggered_builders = trigger_builders_wait
builders = ["nightly"] + triggered_builders

# Supported Yocto Project releases, by name
releases = ["", "sumo", "rocko", "pyro", "morty"]

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
    "nightly-rpm-non-rpm": [],
    "nightly-deb-non-deb": [],
    "default": workers
}
