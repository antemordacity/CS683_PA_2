if [ $# -eq 0 ]; then
    docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/src gcc7-builder
else
    docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/src gcc7-builder ./build_champsim.sh "$@"
fi