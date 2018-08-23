class Instruction(str):
    def __new__(cls, text, start, end=-1):
        return super(Instruction, cls).__new__(cls, text)

    def __init__(self, text, start, end=-1):
        if not isinstance(text, str):
            print("The first parameter should be text")
        if not isinstance(start, int):
            print("The second parameter should be int")
        self.key = text.split(" ")[0]
        self.start_id = start
        if end == -1:
            end = start
        #print("new Istruction instance",text,start,end)
        self.end_id = end

    def __repr__(self):
        return super(Instruction, self).__repr__()
    
    def __str__(self):
        return super(Instruction, self).__str__()

    def __get__(self, instance, owner):
        return super(Instruction, self).__get__()

    @property
    def index(self):
        return self.start_id
    
    @property
    def end(self):
        return self.end_id

    @property
    def size(self):
        return self.end_id - self.start_id + 1

class Dockerfile(list):
    def __init__(self, x=None):
        if isinstance(x, list):
            self.extend(x)
        pass

    def __repr__(self):
        final_repr = bcolors.BOLD+"\nid\tline\tinstruction"+bcolors.ENDC
        for idx, inst in enumerate(self):
            final_repr += "\n"+str(idx)
            if inst.size != 1:
                final_repr += "\t"+str(inst.index)+"-"+str(inst.end)+"\t"
            else:
                final_repr += "\t"+str(inst.index)+"\t"
            if inst.key == "#":
                final_repr += bcolors.OKGREEN+inst+bcolors.ENDC
            elif inst.key in ["RUN","COPY","ADD"]:
                final_repr += bcolors.HEADER+inst+bcolors.ENDC
            else:
                final_repr += inst

        return final_repr
    
    def __str__(self):
        return self.__repr__()                                                                                                         

    def __getitem__(self, key):
        if isinstance(key, int):
            return super(Dockerfile, self).__getitem__(key)
        elif isinstance(key, str):
            return [x for x in self if x.key == key]
    
    def shift(self, where, shift):
        #print("Shifting " + str(shift) + " starting from " + str(where))
        if where < len(self):
            for x in self:
                if x.index < where:
                    continue
                x.start_id += shift
                x.end_id += shift

    def replace(self, x, y):
        print("replace")
        for idx, inst in enumerate(self):
            if inst == x:
                if isinstance(x, str) and isinstance(y, str):
                    y = Instruction(y, inst.index, inst.end)
                self[idx] = y
                #TODO: shift
                break
    
    def remove(self, x):
        print("removing")
        tmp = [inst for inst in self if inst != x]
        self.clear()
        self.extend(tmp)
        self.shift(x.index,-x.size)

    def insert(self, idx, x, size):
        print("insert")
        array_index = -1
        for inst in self:
            array_index = inst.index
            if inst.end >= idx:
                break
        #TODO: handle lists
        super(Dockerfile, self).insert(array_index, Instruction(x,idx,idx+size))
        self.shift(array_index+1,size+1)
        self[array_index+1].start_id += size+1
        self[array_index+1].end_id += size+1
    
    # Number of instructions generating a layer
    @property
    def layers(self):
        return len([x for x in self if x.key in ["RUN","COPY","ADD"]])
    
    # Number of non-comment instructions
    @property
    def len(self):
        return len([x for x in self if x.key != "#"])

# Console colors
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'