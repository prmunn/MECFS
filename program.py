import program_actions
import data.mongo_setup as mongo_setup


def main():
    mongo_setup.global_init()
    program_actions.run()


# if __name__ == '__main__':
#     main()
