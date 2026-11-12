
def recognition_worker(recognition_requests, recognition_results, stop_event):
    try:
        print("recognition init successful")
        while not stop_event.is_set():
            pass
                
    
    finally:
        print("Recognition worker closing.")
        