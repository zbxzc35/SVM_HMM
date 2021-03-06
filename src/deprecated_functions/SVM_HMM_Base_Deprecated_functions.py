'''
Created on Jan 8, 2014

@author: sumanravuri
'''

class SVM_HMM_Base_Deprecated_functions(object):
    '''
    Deprecated Functions SVM HMM Base
    '''
    def find_best_sentence_labels(self, sent_features, do_dot = True):
        if do_dot:
            emission_features = self.classify_dot(sent_features, self.weights.feature_weights, self.weights.bias)
        else:
            emission_features = sent_features
#        num_emission_features = emission_features.shape[0]
        
        label_scores, argmax_features = self.naive_forward_time_chunk(emission_features)
        outputs = self.naive_backtrace(label_scores, argmax_features)
        
        return outputs, label_scores
    
    def classify(self, frame_table = None, sent_indices = None):
        if frame_table is None:
            frame_table = self.frame_table
        if sent_indices is None:
            sent_indices = range(len(frame_table) - 1)
        num_examples = frame_table[-1] - frame_table[0]
#        num_sequences = len(frame_table) - 1
        outputs = np.empty((num_examples,))
        current_frame = 0
        for sent_index in sent_indices:
            chunk_size = frame_table[sent_index + 1] - frame_table[sent_index]
            sent_features, last_sent_index = self.return_sequence_chunk(frame_table, sent_index, chunk_size)
            current_frame = frame_table[sent_index]
            end_frame = frame_table[last_sent_index]#current_frame + frames.shape[0]
            outputs[current_frame:end_frame], loss_scores = self.find_best_sentence_labels(sent_features)
#            print outputs

        try:

            num_correct = np.sum(self.labels == outputs)
            percentage_correct = float(num_correct) / self.labels.size * 100
            print "Got %d of %d correct: %.2f%%" % (num_correct, self.labels.size, percentage_correct)
        except AttributeError:
            pass

        return outputs
    
    def naive_forward_time_chunk(self, emission_features):
        label_scores = np.zeros(emission_features.shape)
        label_scores[0] = emission_features[0]
        argmax_features = np.zeros(emission_features.shape)
        num_emission_features = emission_features.shape[0]
        
        for feature_index in range(1,num_emission_features):
#            previous_time_feature = label_scores[feature_index-1]
#            current_emission_feature = emission_features[feature_index]
            current_time_scores = np.add.outer(label_scores[feature_index-1], emission_features[feature_index])
            current_time_scores += self.weights.time_weights
#            current_time_scores += previous_time_feature.T[:,np.newaxis]
            label_scores[feature_index] = np.max(current_time_scores, axis=0)
            argmax_features[feature_index] = np.argmax(current_time_scores, axis=0)
        label_scores[-1] += self.weights.end_time_weights
        return label_scores, argmax_features
    
    def classify_dot(self, features, weights, bias):
        return np.dot(features, weights)  + bias
    
    def backtrace_parallel_sentence_labels(self, forward_chunk, argmax_chunk, feature_sequence_lens):
        max_sequence_len = np.max(feature_sequence_lens).astype(int)
        num_sequences = feature_sequence_lens.size
        best_labels = -np.ones((num_sequences, max_sequence_len), dtype=np.int32)
        for sequence_index, sequence_len in enumerate(feature_sequence_lens):
            sequence_time_index = sequence_len - 1
#            print forward_chunk[sequence_time_index,:,sequence_index]
            best_labels[sequence_index, sequence_time_index] = np.argmax(forward_chunk[sequence_time_index,:,sequence_index])
            for time_index in range(sequence_time_index,0,-1):
                best_label = best_labels[sequence_index, sequence_time_index]
                best_labels[sequence_index, time_index -1] = argmax_chunk[time_index, best_label, sequence_index]
        
        return best_labels
    
    def fast_backtrace_parallel_sentence_labels(self, forward_chunk, argmax_chunk, feature_sequence_lens):
        max_sequence_len, num_dims, num_sequences = forward_chunk.shape
        num_sequence_index = range(num_sequences)
        num_sequences = feature_sequence_lens.size
        best_labels = -np.ones((num_sequences, max_sequence_len), dtype=np.int32)
        best_labels[:,-1] = np.argmax(forward_chunk[-1,:,:], axis=0)
        for time_index in range(max_sequence_len-1, 0, -1):
            best_labels[:, time_index - 1] = argmax_chunk[time_index, best_labels[:,time_index], num_sequence_index]
        
        return best_labels
    
    def parallel_time_forward_chunk(self, feature_chunk):
        max_sequence_len = feature_chunk.shape[0]
        forward_chunk = np.zeros(feature_chunk.shape)
        argmax_chunk = -np.ones(feature_chunk.shape)
        forward_chunk[:,:,0] = feature_chunk[:,:,0]
        for sequence_index in range(1,max_sequence_len):
            previous_forward_chunk = forward_chunk[sequence_index-1,:,:]
            current_feature_chunk = feature_chunk[sequence_index,:,:]
            time_i_trellis = np.transpose(previous_forward_chunk[:,np.newaxis,:] + self.weights.time_weights[:,:,np.newaxis], (1,0,2)) + current_feature_chunk[:,np.newaxis,:]
            forward_chunk[sequence_index,:,:] = np.max(time_i_trellis,axis=1)
            argmax_chunk[sequence_index,:,:] = np.argmax(time_i_trellis,axis=1)

        return forward_chunk, argmax_chunk
    
    def move_chunks_to_end(self, forward_chunk, argmax_chunk, feature_sequence_lens):
        max_sequence_len, num_dims, num_sequences = forward_chunk.shape
        
        assert max_sequence_len == max(feature_sequence_lens) and num_sequences == len(feature_sequence_lens)
        new_argmax_chunk = -np.ones(argmax_chunk.shape, dtype=np.int32)
        new_forward_chunk = np.zeros(forward_chunk.shape)
        for batch_index, sequence_len in enumerate(feature_sequence_lens):
            new_forward_chunk[(max_sequence_len-sequence_len):,:,batch_index] = forward_chunk[:sequence_len, :, batch_index]
            new_argmax_chunk[(max_sequence_len-sequence_len):,:,batch_index] = argmax_chunk[:sequence_len, :, batch_index]
        
        return new_forward_chunk, new_argmax_chunk
    
    def reshape_chunk(self, features, feature_sequence_lens):
        num_dims = features.shape[1]
        num_sequences = len(feature_sequence_lens)
        max_sequence_len = np.max(feature_sequence_lens)
        output_features = np.zeros((max_sequence_len, num_dims, num_sequences))
        frame_index = 0
        for sent_index, sequence_len in enumerate(feature_sequence_lens):
            end_index = frame_index + sequence_len
            output_features[:sequence_len, :, sent_index] = features[frame_index:end_index, :]
            frame_index = end_index
        return output_features
    
    def flatten_labels(self, labels, feature_sequence_lens):
#        num_sequences, max_sequence_len = labels.shape
        flat_labels = -np.ones(sum(feature_sequence_lens), dtype = np.int32)
        current_frame = 0
        
        for sequence_index, sequence_len in enumerate(feature_sequence_lens):
            flat_labels[current_frame:current_frame+sequence_len] = labels[sequence_index, :sequence_len]
            current_frame += sequence_len
        
        return flat_labels
    
    def flatten_labels_from_back(self, labels, feature_sequence_lens):
        num_sequences, max_sequence_len = labels.shape
        flat_labels = -np.ones(sum(feature_sequence_lens), dtype = np.int32)
        current_frame = 0
        
        for sequence_index, sequence_len in enumerate(feature_sequence_lens):
            flat_labels[current_frame:current_frame+sequence_len] = labels[sequence_index, (max_sequence_len - sequence_len):]
            current_frame += sequence_len
        
        return flat_labels

    def add_bias_to_array(self, data):
        num_examples, num_dims = data.shape
        new_data = np.empty((num_examples, num_dims+1))
        new_data[:,:-1] = data
        new_data[:,-1] = 1.0
        return new_data
     
    def return_parallel_sequence_chunk(self, frame_table, current_sent_index, chunk_size):
        """
        """
        try:
            last_sent_index = np.where(frame_table > chunk_size + frame_table[current_sent_index])[0][0] - 1
        except IndexError: #means that we can read the whole frame table
            last_sent_index = len(frame_table) - 1
        data, sub_frames, sub_labels, sub_frame_table = read_pfile(self.feature_file_name, sent_indices = (current_sent_index, last_sent_index))
        if self.context_window > 1:
            cw_data = context_window(data, self.context_window, False, None, False)
        else:
            cw_data = data
            
        num_examples, num_dims = cw_data.shape
        new_data = np.empty((num_examples, num_dims+1))
        new_data[:,:-1] = cw_data
        new_data[:,-1] = 1.0
#        new_data = np.concatenate((new_data, np.ones((num_examples, 1))), axis=1)
#        print new_data.flags
        return new_data, last_sent_index

    def update_gradient(self, sent_features, sent_labels, most_violated_sequence, gradient):
        """TO BE deprecated in favor of cython version
        """
        num_sent_features = sent_features.shape[0]
        
        gradient.feature_weights[:,sent_labels[0]] -= sent_features[0]
        gradient.feature_weights[:,most_violated_sequence[0]] += sent_features[0]
        
        gradient.bias[sent_labels[0]] -= 1.0
        gradient.bias[most_violated_sequence[0]] += 1.0
        
        gradient.start_time_weights[sent_labels[0]] -= 1.0
        gradient.start_time_weights[most_violated_sequence[0]] += 1.0
        
#        previous_label = sent_labels[0]
#        previous_violated_label = most_violated_sequence[0]
        for observation_index in range(1,num_sent_features):
            feature = sent_features[observation_index]
            current_label = sent_labels[observation_index]
            current_violated_label = most_violated_sequence[observation_index]
#            print current_violated_label, current_label
            gradient.feature_weights[:,current_label] -= feature
            gradient.feature_weights[:,current_violated_label] += feature
            gradient.bias[current_label] -= 1.0
            gradient.bias[current_violated_label] += 1.0
#            previous_label = current_label
#            previous_violated_label = current_violated_label
        
        gradient.time_weights[sent_labels[:-1], sent_labels[1:]] -= 1.0
        gradient.time_weights[most_violated_sequence[:-1], most_violated_sequence[1:]] += 1.0
        
        return gradient