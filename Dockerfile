FROM gcc:7
WORKDIR /src
CMD ["./build_champsim.sh", "baseline"]