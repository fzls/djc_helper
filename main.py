from djc_helper import DjcHelper
from update import check_update_on_start

if __name__ == '__main__':
    check_update_on_start()

    djcHelper = DjcHelper()
    djcHelper.run()
