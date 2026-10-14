if [ $# -eq 0 ]; then
    docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/src gcc7-builder
elif [ "$1" = "spp_v2" ] || [ "$1" = "spp_v1" ] || [ "$1" = "spp_v3" ]; then
    cp prefetcher/"$1".cpp prefetcher/spp.l1d_pref
    docker run --rm --user "$(id -u):$(id -g)" -v "$(pwd)":/src gcc7-builder ./build_champsim.sh spp
else
    echo "Invalid argument."
fi