{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python3Packages = pkgs.python312Packages;
        svgMagick = pkgs.imagemagick.override {
          librsvgSupport = true;
        };
      in
      {
        packages.default = python3Packages.buildPythonApplication rec {
          pname = "pysdfer";
          version = "0.1.0";
          format = "other";

          propagatedBuildInputs = with python3Packages; [
            # List of dependencies
            numpy
            tinycss
            wand
            svgMagick
            pkgs.inkscape
            alive-progress
            xxhash
          ];

          buildInputs = with pkgs; [
          ];

          # Do direct install
          #
          # Add further lines to `installPhase` to install any extra data files if needed.
          dontUnpack = true;
          installPhase = ''
            install -Dm755 ${./pysdfer.py} $out/bin/pysdfer
          '';
        };
        /*
                pkgs.stdenv.mkDerivation {
                  name = "pysdfer";
                  propagatedBuildInputs = [
                    (pkgs.python3.withPackages (
                      pythonPackages: with pythonPackages; [
                      numpy
                      tinycss
                      wand
                      ]
                    ))
                    pkgs.imagemagick
                  ];
                  dontUnpack = true;
                  installPhase = "install -Dm755 ${./pysdfer.py} $out/bin/myscript";
                };
        */
      }

    );
}
