#!/usr/bin/env zsh

########################################################################################################################
# preprocess the original chess piece graphics to correctly sized png images
########################################################################################################################
for dir in *; do
    cd "${dir}"
    if [ -f Black-Pawn.svg ]; then
        for filename in *.svg; do
            # adapted from https://stackoverflow.com/a/14174624
            inkscape -w 60 -h 60 "${filename}" -o $(basename "${filename}" .svg).png
            rm "${filename}"
        done
    fi
    cd ..
done

rm -rf outlined
mkdir -p outlined
cd cburnett
# outlining adapted from: https://stackoverflow.com/a/61442120 & https://stackoverflow.com/a/56431190
for image in Black-*.png; do
    magick                                                                                                             \
        "${image}"                                                                                                     \
        -resize 400%                                                                                                   \
        \(                                                                                                             \
            +clone                                                                                                     \
            -alpha extract                                                                                             \
            -morphology edgeout octagon:4                                                                              \
            -threshold 10%                                                                                             \
            -transparent black                                                                                         \
        \)                                                                                                             \
        -composite                                                                                                     \
        -resize 25%                                                                                                    \
        "../outlined/${image}"
done
cd ..
cp cburnett/White-*.png outlined
