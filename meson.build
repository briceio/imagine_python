project('imagine',  
          version: '0.1.0',
    meson_version: '>= 0.50.0',
  default_options: [ 'warning_level=2',
                   ],
)

i18n = import('i18n')
pymod = import('python')


subdir('data')
subdir('src')
subdir('po')

schemas_dir = get_option('prefix') / get_option('datadir') / 'glib-2.0' / 'schemas'
settings_schemas = [ 'src/io.boite.imagine.gschema.xml' ]

install_data(settings_schemas, install_dir: schemas_dir)

meson.add_install_script('glib-compile-schemas', schemas_dir)
meson.add_install_script('build-aux/meson/postinstall.py')
