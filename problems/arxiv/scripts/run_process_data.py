from problems.arxiv.process_raw_data import ProcessRawData


if __name__ == '__main__':
    # python -m problems.arxiv.scripts.run_process_data

    ProcessRawData.get_click_data(
        ['/Users/saultoscano/Documents/research/GitHub/170203_usage.json.gz'],"test.json")