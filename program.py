from inspector import Inspector
ins = Inspector(scope="./docker")
ins.run()

"""ins.get_context_files()
ins.get_dockerfile_path()
ins.get_dockerfile_instruction_list()
ins.get_dockerfile_instruction_dict()"""