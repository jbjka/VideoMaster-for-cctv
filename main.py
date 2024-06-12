from VideoMaster import VideoMaster
import argparse

def parse_args():
    parse = argparse.ArgumentParser(description="How to use VideoMaster")
    parse.add_argument('-u','--url',type=str,required=True,metavar='',help="cctv video‘s url")
    parse.add_argument('-t','--thread',type=int,required=False,default=10,metavar='',help="Number of threads used to download the video")
    args = parse.parse_args()
    return args

if __name__ == '__main__':
    args = parse_args()
    vm = VideoMaster(args.url,args.thread)
    vm.getTimeFrequency()
    vm.create_download_url()
    print("下载中,请稍等")
    vm.start_download()
    print("视频合并中,请稍等")
    vm.merge()
    print(f'视频的路径是 {vm.get_file_path()}')
