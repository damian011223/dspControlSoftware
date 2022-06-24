class FrequencyHandler:
    def __init__(self, path) -> None:
        self.LUT = {}
        with open(path) as f:
            content = f.readlines()
            for line in content:
                key, value = line.split(',')
                self.LUT[int(key)] = int(round(float(value),0))

    def getFrequency(self, tone):
        return self.LUT[tone]
        
