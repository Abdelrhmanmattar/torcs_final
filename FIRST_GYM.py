import snakeoil as snakeoil
if __name__ == "__main__":
    C= snakeoil.Client()
    for step in range(C.maxSteps,0,-1):
        C.get_servers_input()
        snakeoil.drive_example(C,step)
        C.respond_to_server()
    C.shutdown()