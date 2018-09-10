######################################################################
# Installing buildbot without ability to edit UI
######################################################################

sudo adduser pokybuild3
sudo -iu pokybuild3
pip3 install buildbot
PATH=$PATH:/.local/bin

[FIXME]


######################################################################
# To edit/rebuild UI Plugin
######################################################################

# Ensure prereqs are installed
apt install sudo git build-essential python3-pip virtualenv enchant npm

# Create a new user
sudo adduser pokybuild3
sudo -iu pokybuild3

# Clone the buildbot UI
git clone http://github.com/buildbot/buildbot.git

# Build up the right virtualenv
cd buildbot
make virtualenv VENV_PY_VERSION=python3.6 VENV_NAME=testenv
. testenv/bin/activate

# Build the web frontend components
make frontend VENV_PY_VERSION=python3.6 VENV_NAME=testenv

# Clone our plugin and rebuild it
cd ~
git clone https://git.yoctoproject.org/git/yocto-autobuilder2 yoctoabb
cd ~/yoctoabb/yocto_console_view
python3 setup.py build


######################################################################
# To build/run/edit a test autobuilder
######################################################################

# Create a new user
sudo adduser pokybuild3
sudo -iu pokybuild3

# Clone the buildbot UI
git clone http://github.com/buildbot/buildbot.git

# Build up the right virtualenv
cd buildbot
make virtualenv VENV_PY_VERSION=python3.6 VENV_NAME=testenv
. testenv/bin/activate

# Build the web frontend components
pip install --editable pkg
pip install --editable master/
pip install --editable www/waterfall_view/
pip install --editable www/grid_view/
make frontend VENV_PY_VERSION=python3.6 VENV_NAME=testenv

# Create controller and worker
buildbot create-master ~/yocto-controller
buildbot-worker create-worker ~/yocto-worker localhost example-worker pass --umask=0o22

# Setup the controller
cd ~/yocto-controller
git clone https://git.yoctoproject.org/git/yocto-autobuilder2 yoctoabb
ln -rs yoctoabb/master.cfg master.cfg
<edit master.cfg services.py www.py config.py>
<add ~/config-local.json with contents:>
{
    "BASE_HOMEDIR" : "/home/pokybuild3",
    "BASE_SHAREDDIR" : "/home/pokybuild3/shareddir"
}
export ABHELPER_JSON="config.json /home/pokybuild3/config-local.json"
(or set env in config.py for builders)

# Rebuild our plugin
cd ~/yocto-controller/yoctoabb/yocto_console_view
python3 setup.py build

# Setup the helper
cd ~
git clone https://git.yoctoproject.org/git/yocto-autobuilder-helper

# Startup commands (janitor, controller, worker)
~/yocto-autobuilder-helper/janitor/ab-janitor &
cd buildbot
. testenv/bin/activate
buildbot start ~/yocto-controller
buildbot-worker start ~/yocto-worker







