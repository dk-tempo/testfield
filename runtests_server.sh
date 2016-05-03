#!/usr/bin/env bash

set -o errexit
#set -o nounset
set -o pipefail

if [[ $# -lt 2 || ( "$1" != benchmark && "$1" != "test" ) ]];
then
    echo "Usage: "
    echo "  $0 benchmark name [server_branch] [web_branch] [tag]"
    echo "  $0 test name [server_branch] [web_branch] [tag]"
    exit 1
fi

source config.sh

MYTMPDIR=$SERVER_TMPDIR
ENVNAME=$SERVER_ENVNAME

SERVERDIR=$MYTMPDIR/server
WEBDIR=$MYTMPDIR/web

SESSION_NAME=unifield-$$

VERB=${1:-test}

NAME=${2:-unkown}
SERVERBRANCH=${3:-lp:unifield-server}
WEBBRANCH=${4:-lp:unifield-web}

LETTUCE_PARAMS="${*:5}"

export PGPASSWORD=$DBPASSWORD

PARAM_UNIFIELD_SERVER="--db_user=$DBUSERNAME --db_password=$DBPASSWORD --db_host=$DBADDR -c $MYTMPDIR/openerp-server.conf"

fetch_source_code()
{
    # (1) fetch the source code
    rm -rf $MYTMPDIR/server $MYTMPDIR/web || true
    bzr checkout "$SERVERBRANCH" "$SERVERDIR"
    bzr checkout "$WEBBRANCH" "$WEBDIR"

    # we have to get rid of the versions we don't want
    echo "88888888888888888888888888888888
66f490e4359128c556be7ea2d152e03b 2013-04-27 16:49:56" > $MYTMPDIR/server/bin/unifield-version.txt

    cat $SERVERDIR/bin/openerp-server.py | sed s/"root"/"ssssb"/ >  $SERVERDIR/bin/openerp-server.py.bak
    rm $SERVERDIR/bin/openerp-server.py
    mv $SERVERDIR/bin/openerp-server.py.bak $SERVERDIR/bin/openerp-server.py

}

generate_configuration_file()
{
    # 3. set up the configuration
    rm $MYTMPDIR/openerp-web.cfg $MYTMPDIR/openerp-server.conf 2> /dev/null || true

    cp config/openerp-web.cfg $MYTMPDIR/openerp-web.cfg
    cp config/openerp-server.conf $MYTMPDIR/openerp-server.conf
    # add the specific rules

    BASE64_UNIFIELDPASSWORD=`echo -n "$UNIFIELDPASSWORD" | base64`
    BASE64_DBPASSWORD=`echo -n "$DBPASSWORD" | base64`

    echo """
admin_passwd = $BASE64_UNIFIELDPASSWORD
admin_bkpdb_passwd = $BASE64_UNIFIELDPASSWORD
admin_dropdb_passwd = $BASE64_UNIFIELDPASSWORD
admin_restoredb_passwd = $BASE64_UNIFIELDPASSWORD
db_password = $BASE64_DBPASSWORD
db_port = $DBPORT
xmlrpcs_port = $XMLRPCS_PORT
xmlrpc_port = $XMLRPC_PORT
root_path = $SERVERDIR/bin
netrpc_port = $NETRPC_PORT
    """ >> $MYTMPDIR/openerp-server.conf

    echo """
server.socket_port = $WEB_PORT
openerp.server.port = '$NETRPC_PORT'
    """ >> $MYTMPDIR/openerp-web.cfg
}

upgrade_server()
{
    # at first we have to upgrade all the databases
    for DBNAME in $DATABASES;
    do
        python $SERVERDIR/bin/openerp-server.py $PARAM_UNIFIELD_SERVER -u base --stop-after-init -d $DBNAME
    done
}


run_unifield()
{
    tmux new -d -s $SESSION_NAME -n server "

        tmux new-window -n web \"
        python $WEBDIR/openerp-web.py -c $MYTMPDIR/openerp-web.cfg
        \";

        python $SERVERDIR/bin/openerp-server.py --db_user=$DBUSERNAME --db_password=$DBPASSWORD --db_host=$DBADDR -c $MYTMPDIR/openerp-server.conf
        \""


    case $VERB in

    test)
        export TIME_BEFORE_FAILURE=${TIME_BEFORE_FAILURE:-40}
        export COUNT=2;

        export TEST_DESCRIPTION=$NAME
        export TEST_NAME=$NAME

        rm output/* || true

        ./runtests_local.sh $LETTUCE_PARAMS

        DIREXPORT=website/tests/$NAME
        if [[ -e "$DIREXPORT" ]]
        then
            rm -rf "$DIREXPORT" || true
        fi
        mkdir "$DIREXPORT"

        cp -R output/* $DIREXPORT/ || true

        ;;

    benchmark)
        rm -rf results/* 2> /dev/null || true
        export TIME_BEFORE_FAILURE=

        for count in 5 10 15 20 25 30 35 40
        do
            export COUNT=$count

            # run the benchmark
            for nb in `seq 1 3`;
            do
                ./runtests_local.sh $LETTUCE_PARAMS
            done
        done

        DIREXPORT="website/performances/$NAME"
        if [[ -e "$DIREXPORT" ]]
        then
            rm -rf "$DIREXPORT" || true
        fi
        mkdir "$DIREXPORT"

        cp -R results/* "$DIREXPORT/"

        ;;

    esac

    tmux kill-session -t $SESSION_NAME
}

DATABASES=
for FILENAME in `find instances/$ENVNAME -name *.dump | sort`;
do
    F_WITHOUT_EXTENSION=${FILENAME%.dump}
    DBNAME=${F_WITHOUT_EXTENSION##*/}

    DATABASES="$DATABASES $DBNAME"
done
FIRST_DATABASE=`echo $DATABASES | cut -d " " -f1`

./generate_credentials.sh $FIRST_DATABASE
fetch_source_code;
python restore.py --reset-versions $ENVNAME
generate_configuration_file;

#FIXME: We should do it only if necessary. How can we check that?
upgrade_server;

if [[ -z "$DISPLAY" ]];
then
    tmux new -d -s X_$$ "Xvfb :99"
    export DISPLAY=:99
fi

run_unifield;

