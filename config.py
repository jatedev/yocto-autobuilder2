# ## Build configuration, tied to config.json in yocto-autobuilder-helpers
# Repositories used by each builder
buildertorepos = {
    "eclipse-plugin-neon": ["eclipse-poky-neon"],
    "eclipse-plugin-oxygen": ["eclipse-poky-oxygen"],
    "a-quick": ["poky", "meta-intel", "oecore", "bitbake",
                "meta-mingw", "meta-gplv2"],
    "a-full": ["poky", "meta-intel", "oecore", "bitbake",
                "meta-mingw", "meta-gplv2"],
    "non-gpl3": ["poky", "meta-gplv2"],
    "meta-mingw": ["poky", "meta-mingw"],
    "qa-extras": ["poky", "meta-mingw"],
    "meta-oe": ["poky", "meta-openembedded"],
    "meta-virt": ["poky", "meta-openembedded", "meta-virtualization"],
    "qemuarm-oecore": ["oecore", "bitbake"],
    "checkuri": ["poky"],
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
    "meta-gplv2": ["git://git.yoctoproject.org/meta-gplv2", "master"],
    "meta-openembedded": ["git://git.openembedded.org/meta-openembedded", "master"],
    "meta-virtualization": ["git://git.openembedded.org/meta-openembedded", "master"]
}

trigger_builders_wait_shared = [
    "qemuarm", "qemuarm-lsb", "qemuarm64", "qemuarm-oecore",
    "qemumips", "qemumips64",
    "multilib",
    "qemuppc",
    "qemux86", "qemux86-lsb",
    "qemux86-64", "qemux86-64-lsb",
    "qemux86-64-x32", "qemux86-world",
    "edgerouter",
    "mpc8315e-rdb",
    "genericx86", "genericx86-lsb",
    "genericx86-64", "genericx86-64-lsb",
    "beaglebone", "beaglebone-lsb",
    "pkgman-non-rpm",
    "pkgman-rpm-non-rpm", "pkgman-deb-non-deb",
    "build-appliance", "buildtools",
    "non-gpl3", "wic",
    "poky-tiny", "musl-qemux86", "musl-qemux86-64", "no-x11",
    "qa-extras", "qa-extras2",
    "check-layer", "meta-mingw"
]

trigger_builders_wait_quick = trigger_builders_wait_shared + [
    "oe-selftest", "qemux86-64-ptest-fast"
]

trigger_builders_wait_full = trigger_builders_wait_shared + [
    "qemumips-lsb", "edgerouter-lsb", "mpc8315e-rdb-lsb", "qemuppc-lsb", "qemux86-world-lsb",
    "oe-selftest-ubuntu", "oe-selftest-debian", "oe-selftest-fedora", "oe-selftest-centos",
    "qemux86-64-ptest", "buildperf-ubuntu1604", "buildperf-centos7", "qemux86-64-ltp"
]

# Builders which are individually triggered
builders_others = [
    "meta-oe", "meta-virt",
    "bringup",
    "qemuarm64-ptest",
    "qemuarm64-ptest-fast",
    "qemuarm64-ltp"
]

subbuilders = list(set(trigger_builders_wait_quick + trigger_builders_wait_full + builders_others))
builders = ["a-quick", "a-full"] + subbuilders

# ## Cluster configuration
# Publishing settings
sharedrepodir = "/srv/www/vhosts/repos.yoctoproject.org"
publish_dest = "/srv/www/vhosts/autobuilder.yoctoproject.org/pub"

# Web UI settings
web_port = 8010

# List of workers in the cluster
workers_ubuntu = ["ubuntu1804-ty-1", "ubuntu1804-ty-2", "ubuntu1804-ty-3", "ubuntu1604-ty-1"]
workers_centos = ["centos7-ty-1", "centos7-ty-2", "centos7-ty-3", "centos7-ty-4"]
workers_fedora = ["fedora28-ty-1"]
workers_debian = ["debian9-ty-1", "debian8-ty-1", "debian9-ty-2"]
workers_opensuse = ["opensuse423-ty-1"]

workers = workers_ubuntu + workers_centos + workers_fedora + workers_debian + workers_opensuse 

workers_bringup = ["fedora29-ty-1", "opensuse150-ty-1"]
# workers with wine on them for meta-mingw
workers_wine = ["ubuntu1804-ty-1", "ubuntu1804-ty-2", "ubuntu1804-ty-3"]
workers_buildperf = ["perf-ubuntu1604", "perf-centos7"]

all_workers = workers + workers_bringup + workers_buildperf

# Worker configuration, all workers configured the same...
# TODO: support per-worker config
worker_password = "pass"
worker_max_builds = None
notify_on_missing = None

# Some builders should only run on specific workers (host OS dependent)
builder_to_workers = {
    "bringup": workers_bringup,
    "pkgman-rpm-non-rpm": workers_ubuntu + workers_debian,
    "pkgman-deb-non-deb": workers_fedora + workers_centos + workers_opensuse,
    "oe-selftest-ubuntu": workers_ubuntu,
    "oe-selftest-debian": workers_debian,
    "oe-selftest-fedora": workers_fedora,
    "oe-selftest-opensuse": workers_opensuse,
    "oe-selftest-centos": workers_centos,
    "meta-mingw": workers_wine,
    "buildperf-ubuntu1604": "perf-ubuntu1604",
    "buildperf-centos7": "perf-centos7",
    "default": workers
}
