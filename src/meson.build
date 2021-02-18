pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'imagine')
gnome = import('gnome')

gnome.compile_resources('imagine',
  'imagine.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'imagine.in',
  output: 'imagine',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

imagine_sources = [
  '__init__.py',
  'main.py',
  'layers.py',
  'document.py',
  'window.py',
  'layer_editor.py',
  'resize_dialog.py',
  'tools.py',
]

install_data(imagine_sources, install_dir: moduledir)
