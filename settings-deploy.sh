#!/bin/zsh
cp ./src/io.boite.imagine.gschema.xml /usr/share/glib-2.0/schemas/
glib-compile-schemas /usr/share/glib-2.0/schemas/
