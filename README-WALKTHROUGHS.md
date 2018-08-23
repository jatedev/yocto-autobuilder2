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

# Create a new user
sudo adduser pokybuild3
sudo -iu pokybuild3

# Clone the buildbot UI
git clone http://github.com/buildbot/buildbot.git

# Build up the right virtualenv
cd buildbot
make virtualenv VENV_PY_VERSION=python3.6 VENV_NAME=testenv
export VENV_PY_VERSION=python3.6 
export VENV_NAME=testenv
. testenv/bin/activate

# Build the web frontend components
make frontend

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
export VENV_PY_VERSION=python3.6 
export VENV_NAME=testenv
. testenv/bin/activate

# Build the web frontend components
pip install --editable pkg
pip install --editable master/
pip install --editable www/waterfall_view/
pip install --editable www/grid_view/
make frontend

# Create controller and worker
buildbot create-master ~/yocto-controller
buildbot-worker create-worker ~/yocto-worker localhost example-worker pass

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
(set set env in config.py)

# Rebuild our plugin
cd ~/yoctoabb/yocto_console_view
python3 setup.py build

# Setup the helper
cd ~
git clone https://git.yoctoproject.org/git/yocto-autobuilder-helper

# Startup commands (janitor, controller, worker)
~/yocto-autobuilder-helper/janitor/ab-janitor
buildbot start ~/yocto-controller
buildbot-worker start ~/yocto-worker







