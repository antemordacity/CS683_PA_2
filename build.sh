read $user_input
if ["$user_input" == ""] ; then
    docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/src gcc7-builder
else
    docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/src gcc7-builder ./build_champsim.sh $user_input
fi